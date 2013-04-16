#Python
from functools import partial

#Qt
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QMenu, QAction, QDialog, QHBoxLayout, QTableWidget, QSizePolicy, QTableWidgetItem, QColor

#volumina
from volumina.layer import ColortableLayer, GrayscaleLayer, RGBALayer, ClickableColortableLayer
from layerDialog import GrayscaleLayerDialog, RGBALayerDialog
from exportDlg import ExportDialog

#===----------------------------------------------------------------------------------------------------------------===

###
### lazyflow input
###
_has_lazyflow = True
try:
    from lazyflow.graph import Graph
    from lazyflow.operators.operators import OpArrayPiper
except ImportError as e:
    exceptStr = str(e)
    _has_lazyflow = False

def _add_actions_grayscalelayer( layer, menu ):
    def adjust_thresholds_callback():
        dlg = GrayscaleLayerDialog(layer, menu.parent())
        dlg.show()
        
    adjThresholdAction = QAction("Adjust thresholds", menu)
    adjThresholdAction.triggered.connect(adjust_thresholds_callback)
    menu.addAction(adjThresholdAction)

def _add_actions_rgbalayer( layer, menu ): 
    def adjust_thresholds_callback():
        dlg = RGBALayerDialog(layer, menu.parent())
        dlg.show()

    adjThresholdAction = QAction("Adjust thresholds", menu)
    adjThresholdAction.triggered.connect(adjust_thresholds_callback)
    menu.addAction(adjThresholdAction)
 
class LayerColortableDialog(QDialog):
    def __init__(self, layer, parent=None):
        super(LayerColortableDialog, self).__init__(parent=parent)
        
        h = QHBoxLayout(self)
        t = QTableWidget(self)
        t.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)       
        t.setRowCount(len(layer._colorTable))
        t.setColumnCount(1)
        t.setVerticalHeaderLabels(["%d" %i for i in range(len(layer._colorTable))])
        
        for i in range(len(layer._colorTable)): 
            item = QTableWidgetItem(" ")
            t.setItem(i,0, item);
            item.setBackgroundColor(QColor.fromRgba(layer._colorTable[i]))
            item.setFlags(Qt.ItemIsSelectable)
        
        h.addWidget(t)
    
def _add_actions_colortablelayer( layer, menu ): 
    def adjust_colortable_callback():
        dlg = LayerColortableDialog(layer, menu.parent())
        dlg.exec_()
        
    adjColortableAction = QAction("Change colortable", menu)
    adjColortableAction.triggered.connect(adjust_colortable_callback)
    menu.addAction(adjColortableAction)
    if layer.colortableIsRandom:
        randomizeColors = QAction("Randomize colors", menu)
        randomizeColors.triggered.connect(layer.randomizeColors)
        menu.addAction(randomizeColors)

def _add_actions( layer, menu ):
    if isinstance(layer, GrayscaleLayer):
        _add_actions_grayscalelayer( layer, menu )
    elif isinstance( layer, RGBALayer ):
        _add_actions_rgbalayer( layer, menu )
    elif isinstance( layer, ColortableLayer ) or isinstance( layer, ClickableColortableLayer ):
        _add_actions_colortablelayer( layer, menu )

def layercontextmenu( layer, pos, parent=None, volumeEditor = None ):
    '''Show a context menu to manipulate properties of layer.

    layer -- a volumina layer instance
    pos -- QPoint 

    '''
    def onExport():
        dataSource = layer.datasources[0]
        if not hasattr(dataSource, "dataSlot"):
            raise RuntimeError("can not export from a non-lazyflow data source (layer=%r, datasource=%r)" % (type(layer), type(dataSource)) )
        expDlg = ExportDialog(parent = menu)
        import lazyflow
        assert isinstance(dataSource.dataSlot, lazyflow.graph.Slot), "slot is of type %r" % (type(dataSource.dataSlot))
        assert isinstance(dataSource.dataSlot.getRealOperator(), lazyflow.graph.Operator), "slot's operator is of type %r" % (type(dataSource.dataSlot.getRealOperator()))
        expDlg.setInput(dataSource.dataSlot)
            
        expDlg.show()
        
    menu = QMenu("Menu", parent)
    title = QAction("%s" % layer.name, menu)
    title.setEnabled(False)
    
    export = QAction("Export...",menu)
    export.setStatusTip("Export Layer...")
    export.triggered.connect(onExport)
    
    menu.addAction(title)
    menu.addAction(export)
    menu.addSeparator()
    _add_actions( layer, menu )

    menu.addSeparator()
    for name, callback in layer.contexts:
        action = QAction(name, menu)
        action.triggered.connect(callback)
        menu.addAction(action)

    menu.exec_(pos)    
