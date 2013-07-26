import os

from PyQt4 import uic
from PyQt4.QtGui import QWidget, QFileDialog

class NpyExportFileOptionsWidget(QWidget):
    
    def __init__(self, parent):
        super( NpyExportFileOptionsWidget, self ).__init__(parent)
        uic.loadUi( os.path.splitext(__file__)[0] + '.ui', self )

    def initSlot(self, filepathSlot):        
        self._filepathSlot = filepathSlot
        self.fileSelectButton.clicked.connect( self._browseForFilepath )

    def showEvent(self, event):
        super(NpyExportFileOptionsWidget, self).showEvent(event)
        self.updateFromSlot()
        
    def updateFromSlot(self):
        if self._filepathSlot.ready():
            file_path = self._filepathSlot.value
            file_path = os.path.splitext(file_path)[0] + ".npy"
            self.filepathEdit.setText( file_path )
            
            # Re-configure the slot in case we changed the extension
            self._filepathSlot.setValue( str(file_path) )
    
    def _browseForFilepath(self):
        starting_dir = os.path.expanduser("~")
        if self._filepathSlot.ready():
            starting_dir = os.path.split(self._filepathSlot.value)[0]
        
        dlg = QFileDialog( self, "Export Location", starting_dir, "numpy files (*.npy)" )
        dlg.setDefaultSuffix("npy")
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        if not dlg.exec_():
            return
        
        exportPath = dlg.selectedFiles()[0]
        self._filepathSlot.setValue( str(exportPath) )
        self.filepathEdit.setText( exportPath )

if __name__ == "__main__":
    from PyQt4.QtGui import QApplication
    from lazyflow.graph import Graph
    from lazyflow.operators.ioOperators import OpNpyWriter

    op = OpNpyWriter(graph=Graph())

    app = QApplication([])
    w = NpyExportFileOptionsWidget(None)
    w.initSlot(op.Filepath)
    w.show()
    app.exec_()

    print "Selected Filepath: {}".format( op.Filepath.value )


