from PyQt4.QtCore import QObject, pyqtSignal, QEvent, Qt, QPoint

class ClickReportingInterpreter(QObject):
    rightClickReceived = pyqtSignal(object, QPoint) # list of indexes, global window coordinate of click
    leftClickReceived = pyqtSignal(object, QPoint)  # ditto
    
    def __init__(self, navigationInterpreter, positionModel):
        QObject.__init__(self)
        self.baseInterpret = navigationInterpreter
        self.posModel      = positionModel

    def start( self ):
        self.baseInterpret.start()

    def stop( self ):
        self.baseInterpret.stop()

    def eventFilter( self, watched, event ):
        if event.type() == QEvent.MouseButtonPress:
            pos = [int(i) for i in self.posModel.cursorPos]
            pos = [self.posModel.time] + pos + [self.posModel.channel]

            if event.button() == Qt.LeftButton:
                gPos = watched.mapToGlobal( event.pos() )
                self.leftClickReceived.emit( pos, gPos )
            if event.button() == Qt.RightButton:
                gPos = watched.mapToGlobal( event.pos() )
                self.rightClickReceived.emit( pos, gPos )                

        # Event is always forwarded to the navigation interpreter.
        return self.baseInterpret.eventFilter(watched, event)



class ClickInterpreter(QObject):
    """Intercepts mouse clicks (right clicks by default) and double
       click events on a layer and calls a given functor with the
       clicked position.

    """
       
    def __init__(self, editor, layer, onClickFunctor, parent=None, right=True, double=True):
        """ editor:         VolumeEditor object
            layer:          Layer instance on which was clicked
            onClickFunctor: a function f(layer, position5D, windowPosition)
            right: If True, intercept right clicks, otherwise intercept left clicks.
        """
        QObject.__init__(self, parent)
        self.baseInterpret = editor.navInterpret
        self.posModel      = editor.posModel
        self._onClick = onClickFunctor
        self._layer = layer
        if right:
            self.button = Qt.RightButton
        else:
            self.button = Qt.LeftButton
        self.double = double

    def start( self ):
        self.baseInterpret.start()

    def stop( self ):
        self.baseInterpret.stop()

    def eventFilter( self, watched, event ):
        etype = event.type()
        handle = False
        if etype == QEvent.MouseButtonPress and event.button() == self.button:
            handle = True
        if etype == QEvent.MouseButtonDblClick and self.double and event.button() == self.button:
            handle = True
        if etype == QEvent.MouseButtonPress and event.modifiers() == Qt.ShiftModifier:
            handle = False #dragging
        if handle:
            pos = self.posModel.cursorPos
            pos = [int(i) for i in pos]
            pos = [self.posModel.time] + pos + [self.posModel.channel]
            self._onClick(self._layer, tuple(pos), event.pos())
            return True
        else:
            return self.baseInterpret.eventFilter(watched, event)
