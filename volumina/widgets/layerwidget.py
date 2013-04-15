import warnings
from PyQt4.QtGui import QStyledItemDelegate, QWidget, QListView, QStyle, \
                        QAbstractItemView, QPainter, QItemSelectionModel, \
                        QColor, QMenu, QAction, QFontMetrics, QFont, QImage, \
                        QBrush, QPalette, QMouseEvent, QVBoxLayout, QLabel, QGridLayout, QPixmap, \
                        QPushButton, QSpinBox
from PyQt4.QtCore import pyqtSignal, Qt, QEvent, QRect, QSize, QTimer, \
                         QPoint

from volumina.layer import Layer
from layercontextmenu import layercontextmenu

from os import path
from volumina.layerstack import LayerStackModel
import volumina.icons_rc

class FractionSelectionBar( QWidget ):
    fractionChanged = pyqtSignal(float)

    def __init__( self, initial_fraction=1., parent=None ):
        QWidget.__init__( self, parent=parent )
        self._fraction = initial_fraction
        self._lmbDown = False

    def fraction( self ):
        return self._fraction

    def setFraction( self, value ):
        if value == self._fraction:
            return
        if(value < 0.):
            value = 0.
            warnings.warn("FractionSelectionBar.setFraction(): value has to be between 0. and 1. (was %s); setting to 0." % str(value))
        if(value > 1.):
            value = 1.
            warnings.warn("FractionSelectionBar.setFraction(): value has to be between 0. and 1. (was %s); setting to 1." % str(value))
        self._fraction = float(value)
        self.update()

    def mouseMoveEvent(self, event):
        if self._lmbDown:
            self.setFraction(self._fractionFromPosition( event.posF() ))
            self.fractionChanged.emit(self._fraction)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            return
        self._lmbDown = True
        self.setFraction(self._fractionFromPosition( event.posF() ))
        self.fractionChanged.emit(self._fraction)

    def mouseReleaseEvent(self, event):
        self._lmbDown = False

    def paintEvent( self, ev ):
        painter = QPainter(self)

        # calc bar offset
        y_offset =(self.height() - self._barHeight()) // 2
        ## prevent negative offset
        y_offset = 0 if y_offset < 0 else y_offset

        # frame around fraction indicator
        painter.setBrush(self.palette().dark())
        painter.save()
        ## no fill color
        b = painter.brush(); b.setStyle(Qt.NoBrush); painter.setBrush(b)
        painter.drawRect(
            QRect(QPoint(0, y_offset),
                  QSize(self._barWidth(), self._barHeight())))
        painter.restore()

        # fraction indicator
        painter.drawRect(
            QRect(QPoint(0, y_offset),
                  QSize(self._barWidth()*self._fraction, self._barHeight())))

    def sizeHint( self ):
        return QSize(100, 10)

    def minimumSizeHint( self ):
        return QSize(1, 3)

    def _barWidth( self ):
        return self.width()-1

    def _barHeight( self ):
        return self.height()-1

    def _fractionFromPosition( self, pointf ):
        frac = pointf.x() / self.width()
        # mouse has left the widget
        if frac < 0.:
            frac = 0.
        if frac > 1.:
            frac = 1.
        return frac

class ToggleEye( QLabel ):
    activeChanged = pyqtSignal( bool )

    def __init__( self, parent=None ):
        QWidget.__init__( self, parent=parent )
        self._active = True
        self._eye_open = QPixmap(":icons/icons/stock-eye-20.png")
        self._eye_closed = QPixmap(":icons/icons/stock-eye-20-gray.png")
        self.setPixmap(self._eye_open)

    def active( self ):
        return self._active

    def setActive( self, b ):
        if b == self._active:
            return
        self._active = b
        if b:
            self.setPixmap(self._eye_open)
        else:
            self.setPixmap(self._eye_closed)

    def toggle( self ):
        if self.active():
            self.setActive( False )
        else:
            self.setActive( True )

    def mousePressEvent( self, ev ):
        self.toggle()
        self.activeChanged.emit( self._active )

class LayerItemWidget( QWidget ):
    @property
    def layer(self):
        return self._layer
    @layer.setter
    def layer(self, layer):
        if self._layer:
            self._layer.changed.disconnect(self._updateState)
        self._layer = layer
        self._updateState()
        self._layer.changed.connect(self._updateState)

    def __init__( self, parent=None ):
        QWidget.__init__( self, parent=parent )
        print "CREATION"
        self._layer = None

        self._font = QFont(QFont().defaultFamily(), 9)
        self._fm = QFontMetrics( self._font )
        self._bar = FractionSelectionBar( initial_fraction = 0. )
        self._bar.setFixedHeight(10)
        self._nameLabel = QLabel()
        self._nameLabel.setFont( self._font )
        self._nameLabel.setText( "None" )
        self._opacityLabel = QLabel()
        self._opacityLabel.setAlignment(Qt.AlignRight)
        self._opacityLabel.setFont( self._font )
        self._opacityLabel.setText( u"\u03B1=%0.1f%%" % (100.0*(self._bar.fraction())))
        self._toggleEye = ToggleEye()
        self._toggleEye.setActive(False)
        self._toggleEye.setFixedWidth(35)
        self._toggleEye.setToolTip("Visibility")
        self._channelSelector = QSpinBox()
        self._channelSelector.setFrame( False )
        self._channelSelector.setFont( self._font )
        self._channelSelector.setMaximumWidth( 35 )
        self._channelSelector.setAlignment(Qt.AlignRight)
        self._channelSelector.setToolTip("Channel")
        self._channelSelector.setVisible(False)

        self._layout = QGridLayout()
        self._layout.addWidget( self._toggleEye, 0, 0 )
        self._layout.addWidget( self._nameLabel, 0, 1 )
        self._layout.addWidget( self._opacityLabel, 0, 2 )
        self._layout.addWidget( self._channelSelector, 1, 0)
        self._layout.addWidget( self._bar, 1, 1, 1, 2 )

        self._layout.setColumnMinimumWidth( 0, 35 )
        self._layout.setSpacing(0)
        self._layout.setContentsMargins(5,2,5,2)

        self.setLayout( self._layout)

        self._bar.fractionChanged.connect( self._onFractionChanged )
        self._toggleEye.activeChanged.connect( self._onEyeToggle )

    def _onFractionChanged( self, fraction ):
        if self._layer and (fraction != self._layer.opacity):
            self._layer.opacity = fraction

    def _onEyeToggle( self, active ):
        if self._layer and (active != self._layer.visible):
            self._layer.visible = active

    def _updateState( self ):
        if self._layer:
            self._toggleEye.setActive(self._layer.visible)
            self._bar.setFraction( self._layer.opacity )
            self._opacityLabel.setText( u"\u03B1=%0.1f%%" % (100.0*(self._bar.fraction())))
            self._nameLabel.setText( self._layer.name )
            
            if self._layer.numberOfChannels > 1:
                self._channelSelector.setVisible(True)
                self._channelSelector.setMaximum(self._layer.numberOfChannels)
            self.update()

class LayerDelegate(QStyledItemDelegate):
    def __init__(self, layersView, listModel, parent = None):
        QStyledItemDelegate.__init__(self, parent)
        self.currentIndex = -1
        self._view = layersView
        self._editors = {}
        self._w = LayerItemWidget()
        self._listModel = listModel
        self._listModel.rowsAboutToBeRemoved.connect(self.handleRemovedRows)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

    def paint(self, painter, option, index):
        if option.state & QStyle.State_Selected:
            modelIndex = index.row()
            if modelIndex != self.currentIndex:
                model = index.model()
                self.currentIndex = modelIndex
                model.wantsUpdate()

        layer = index.data().toPyObject()
        if isinstance(layer, Layer):
            pic = QPixmap( option.rect.width(), option.rect.height() )
            w = self._w
            w.layer = layer
            w.setGeometry( option.rect )
            w.setAutoFillBackground(True)
            w.setPalette( option.palette )
            w.render(pic)            
            painter.drawPixmap( option.rect, pic )
        else:
            QStyledItemDelegate.paint(self, painter, option, index)

    def sizeHint(self, option, index):
        layer = index.data().toPyObject()
        if isinstance(layer, Layer):
            w = LayerItemWidget()
            return w.sizeHint()
        else:
            return QStyledItemDelegate.sizeHint(self, option, index)

    def createEditor(self, parent, option, index):
        layer = index.data().toPyObject()
        if isinstance(layer, Layer):
            editor = LayerItemWidget(parent=parent)
            editor.setAutoFillBackground(True)
            editor.setPalette( option.palette )
            editor.setBackgroundRole(QPalette.Highlight)
            editor.layer = layer
            self._editors[layer] = editor
            return editor
        else:
            QStyledItemDelegate.createEditor(self, parent, option, index)

    def setEditorData(self, editor, index):
        layer = index.data().toPyObject()
        if isinstance(layer, Layer):
            editor.layer = layer
        else:
            QStyledItemDelegate.setEditorData(self, editor, index)

    def setModelData(self, editor, model, index):
        layer = index.data().toPyObject()
        if isinstance(layer, Layer):
            model.setData(index, editor.layer)
        else:
            QStyledItemDelegate.setModelData(self, editor, model, index)

    def handleRemovedRows(self, parent, start, end):
        for row in range(start, end):
            itemData = self._listModel.itemData( self._listModel.index(row) )
            layer = itemData[Qt.EditRole].toPyObject()
            assert isinstance(layer, Layer)
            if layer in self._editors:
                del self._editors[layer]

    def commitAndCloseEditor(self):
        editor = sender()
        self.commitData.emit(editor)
        self.closeEditor.emit(editor)

class LayerWidget(QListView):
    def __init__(self, parent = None, model=None):

        QListView.__init__(self, parent)

        if model is None:
            model = LayerStackModel()
        self.init(model)

    def init(self, listModel):
        self.setModel(listModel)
        self._itemDelegate = LayerDelegate( self, listModel )
        self.setItemDelegate(self._itemDelegate)
        self.setSelectionModel(listModel.selectionModel)
        #self.setDragDropMode(self.InternalMove)
        self.installEventFilter(self)
        #self.setDragDropOverwriteMode(False)
        self.model().selectionModel.selectionChanged.connect(self.onSelectionChanged)
        QTimer.singleShot(0, self.selectFirstEntry)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up or event.key() == Qt.Key_Down:
            return super(LayerWidget, self).keyPressEvent(event)

        if event.key() == Qt.Key_Right or event.key() == Qt.Key_Left:
            row = self.model().selectedRow()
            if row < 0:
                return
            layer = self.model()[row]

            if event.key() == Qt.Key_Right:
                if layer.opacity < 1.0:
                    layer.opacity = min(1.0, layer.opacity + 0.01)
            elif event.key() == Qt.Key_Left:
                if layer.opacity > 0.0:
                    layer.opacity = max(0.0, layer.opacity - 0.01)

    def resizeEvent(self, e):
        self.updateGUI()
        QListView.resizeEvent(self, e)

    def contextMenuEvent(self, event):
        idx = self.indexAt(event.pos())
        layer = self.model()[idx.row()]
        #print "Context menu for layer '%s'" % layer.name

        layercontextmenu( layer, self.mapToGlobal(event.pos()), self )

    def selectFirstEntry(self):
        #self.setEditTriggers(QAbstractItemView.DoubleClicked)
        self.model().selectionModel.setCurrentIndex(self.model().index(0), QItemSelectionModel.SelectCurrent)
        self.updateGUI()

    def updateGUI(self):
        self.openPersistentEditor(self.model().selectedIndex())

    def eventFilter(self, sender, event):
        #http://stackoverflow.com/questions/1224432/
        #how-do-i-respond-to-an-internal-drag-and-drop-operation-using-a-qlistwidget
        if (event.type() == QEvent.ChildRemoved):
            self.onOrderChanged()
        return False

    def onSelectionChanged(self, selected, deselected):
        if len(deselected) > 0:
            self.closePersistentEditor(deselected[0].indexes()[0])
        self.updateGUI()

    def onOrderChanged(self):
        self.updateGUI()

    # def mousePressEvent(self, event):
    #     prevIndex = self.model().selectedIndex()
    #     newIndex = self.indexAt( event.pos() )
    #     super(LayerWidget, self).mousePressEvent(event)

    #     # HACK: The first click merely gives focus to the list item without actually passing the event to it.
    #     # We'll simulate a mouse click on the item by calling mousePressEvent() and mouseReleaseEvent on the appropriate editor
    #     if prevIndex != newIndex and newIndex.row() != -1:
    #         layer = self.model().itemData(newIndex)[Qt.EditRole].toPyObject()
    #         assert isinstance(layer, Layer)
    #         editor = self._itemDelegate._editors[layer]
    #         editorPos = event.pos() - editor.geometry().topLeft()
    #         editorPress = QMouseEvent( QMouseEvent.MouseButtonPress, editorPos, event.button(), event.buttons(), event.modifiers() )
    #         editor.mousePressEvent(editorPress)
    #         editorRelease = QMouseEvent( QMouseEvent.MouseButtonRelease, editorPos, event.button(), event.buttons(), event.modifiers() )
    #         editor.mouseReleaseEvent(editorRelease)

#*******************************************************************************
# i f   _ _ n a m e _ _   = =   " _ _ m a i n _ _ "                            *
#*******************************************************************************

if __name__ == "__main__":
    #make the program quit on Ctrl+C
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    import sys, numpy

    from PyQt4.QtGui import QApplication, QPushButton, QHBoxLayout, QVBoxLayout
    from volumina.pixelpipeline.datasources import ArraySource

    app = QApplication(sys.argv)

    model = LayerStackModel()

    o1 = Layer()
    o1.name = "Fancy Layer"
    o1.opacity = 0.5
    model.append(o1)

    o2 = Layer()
    o2.name = "Some other Layer"
    o2.opacity = 0.25
    o2.numberOfChannels = 3
    model.append(o2)

    o3 = Layer()
    o3.name = "Invisible Layer"
    o3.opacity = 0.15
    o3.visible = False
    model.append(o3)

    o4 = Layer()
    o4.name = "Fancy Layer II"
    o4.opacity = 0.95
    model.append(o4)

    o5 = Layer()
    o5.name = "Fancy Layer III"
    o5.opacity = 0.65
    model.append(o5)

    o6 = Layer()
    o6.name = "Lazyflow Layer"
    o6.opacity = 1

    testVolume = numpy.random.rand(100,100,100,3).astype('uint8')
    source = [ArraySource(testVolume)]
    o6._datasources = source
    model.append(o6)

    view = LayerWidget(None, model)
    view.show()
    view.updateGeometry()

    w = QWidget()
    lh = QHBoxLayout(w)
    lh.addWidget(view)

    up   = QPushButton('Up')
    down = QPushButton('Down')
    delete = QPushButton('Delete')
    add = QPushButton('Add')
    lv  = QVBoxLayout()
    lh.addLayout(lv)

    lv.addWidget(up)
    lv.addWidget(down)
    lv.addWidget(delete)
    lv.addWidget(add)

    w.setGeometry(100, 100, 800,600)
    w.show()

    up.clicked.connect(model.moveSelectedUp)
    model.canMoveSelectedUp.connect(up.setEnabled)
    down.clicked.connect(model.moveSelectedDown)
    model.canMoveSelectedDown.connect(down.setEnabled)
    delete.clicked.connect(model.deleteSelected)
    model.canDeleteSelected.connect(delete.setEnabled)
    def addRandomLayer():
        o = Layer()
        o.name = "Layer %d" % (model.rowCount()+1)
        o.opacity = numpy.random.rand()
        o.visible = bool(numpy.random.randint(0,2))
        model.append(o)
    add.clicked.connect(addRandomLayer)

    app.exec_()
