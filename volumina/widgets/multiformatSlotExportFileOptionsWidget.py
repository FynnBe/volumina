import os
import collections

from PyQt4 import uic
from PyQt4.QtGui import QWidget

from singleFileExportOptionsWidget import SingleFileExportOptionsWidget
from hdf5ExportFileOptionsWidget import Hdf5ExportFileOptionsWidget

class MultiformatSlotExportFileOptionsWidget(QWidget):
    
    def __init__(self, parent):
        super( MultiformatSlotExportFileOptionsWidget, self ).__init__(parent)
        uic.loadUi( os.path.splitext(__file__)[0] + '.ui', self )

    def initExportOp(self, opExportSlot):
        self._opExportSlot = opExportSlot
        self.hdf5OptionsWidget = Hdf5ExportFileOptionsWidget( self )
        self.hdf5OptionsWidget.initSlots( opExportSlot.OutputFilenameFormat,
                                          opExportSlot.OutputInternalPath )

        self.npyOptionsWidget = SingleFileExportOptionsWidget( self, "npy", "numpy files (*.npy)" )
        self.npyOptionsWidget.initSlot( opExportSlot.OutputFilenameFormat )

        self.pngOptionsWidget = SingleFileExportOptionsWidget( self, "png", "PNG files (*.png)" )
        self.pngOptionsWidget.initSlot( opExportSlot.OutputFilenameFormat )

        # Specify our supported formats and their associated property widgets
        # TODO: Explicitly reconcile this with the OpExportSlot.FORMATS
        # TODO: Only include formats that can export the current dataset (e.g. don't include 2D formats for a 3D image)
        self._format_option_editors = \
            collections.OrderedDict([ ('hdf5', self.hdf5OptionsWidget),
                                      ('npy', self.npyOptionsWidget),
                                      ('png', self.pngOptionsWidget) ])

        # Populate the format combo
        for file_format, widget in self._format_option_editors.items():
            self.formatCombo.addItem( file_format )

        # Populate the stacked widget
        # (Some formats use the same options widget; eliminate repeats first)
        all_widgets = set( self._format_option_editors.values() )
        for widget in all_widgets:
            self.stackedWidget.addWidget( widget )
        
        self.formatCombo.currentIndexChanged.connect( self._handleFormatChange )

        # Determine starting format
        index = self.formatCombo.findText(opExportSlot.OutputFormat.value)
        self.formatCombo.setCurrentIndex(index)
        self._handleFormatChange(index)
        
    def _handleFormatChange(self, index):
        file_format = str( self.formatCombo.currentText() )
        option_widget = self._format_option_editors[file_format]
        self.stackedWidget.setCurrentWidget( option_widget )
        self._opExportSlot.OutputFormat.setValue( file_format )

if __name__ == "__main__":
    from PyQt4.QtGui import QApplication
    from lazyflow.graph import Graph, Operator, InputSlot

    class OpMock(Operator):
        OutputFilenameFormat = InputSlot(value='~/something.h5')
        OutputInternalPath = InputSlot(value='volume/data')
        OutputFormat = InputSlot(value='hdf5')
        
        def setupOutputs(self): pass
        def execute(self, *args): pass
        def propagateDirty(self, *args): pass
    
    op = OpMock( graph=Graph() )

    app = QApplication([])
    w = MultiformatSlotExportFileOptionsWidget(None)
    w.initExportOp(op)
    w.show()
    app.exec_()

    print "Selected Filepath: {}".format( op.OutputFilenameFormat.value )
    print "Selected Dataset: {}".format( op.OutputInternalPath.value )



