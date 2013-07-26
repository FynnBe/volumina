import os
import collections
from functools import partial

import numpy

from PyQt4 import uic
from PyQt4.QtCore import Qt, QObject, QEvent
from PyQt4.QtGui import QDialog, QValidator, QDialogButtonBox

from lazyflow.graph import Operator, InputSlot, OutputSlot

#**************************************************************************
# Model operator interface ABC
#**************************************************************************
class ExportOperatorABC(Operator):
    """
    The export dialog is designed to work with any operator that satisfies this ABC interface.
    """
    # Operator.__metaclass__ already inherits ABCMeta
    # __metaclass__ = ABCMeta
    
    Input = InputSlot()

    # Subregion params
    RegionStart = InputSlot(optional=True)
    RegionStop = InputSlot(optional=True)

    # Normalization params    
    InputMin = InputSlot(optional=True)
    InputMax = InputSlot(optional=True)
    ExportMin = InputSlot(optional=True)
    ExportMax = InputSlot(optional=True)

    ExportDtype = InputSlot(optional=True)
    OutputAxisOrder = InputSlot(optional=True)
    
    # File settings
    OutputFilenameFormat = InputSlot(value='RESULTS_{roi}') # A format string allowing {roi}, {x_start}, {x_stop}, etc.
    OutputInternalPath = InputSlot(value='exported_data')
    OutputFormat = InputSlot(value='hdf5')

    ConvertedImage = OutputSlot() # Preprocessed image, BEFORE axis reordering
    ImageToExport = OutputSlot() # Preview of the pre-processed image that will be exported
    ExportPath = OutputSlot() # Location of the saved file after export is complete.

    @classmethod
    def __subclasshook__(cls, C):
        # Must have all the required input and output slots.
        if cls is ExportOperatorABC:
            for slot in cls.inputSlots:
                if not hasattr(C, slot.name) or not isinstance(getattr(C, slot.name), InputSlot):
                    return False
            for slot in cls.outputSlots:
                if not hasattr(C, slot.name) or not isinstance(getattr(C, slot.name), OutputSlot):
                    return False
            return True
        return NotImplemented

#**************************************************************************
# DataExportOptionsDlg
#**************************************************************************
class DataExportOptionsDlg(QDialog):
    
    def __init__(self, parent, opExportSlot):
        """
        Constructor.
        
        :param parent: The parent widget
        :param opExportSlot: The operator to configure.  The operator is manipulated LIVE, so supply a 
                             temporary operator that can be discarded in case the user clicked 'cancel'.
                             If the user clicks 'OK', then copy the slot settings from the temporary op to your real one.
        """
        super( DataExportOptionsDlg, self ).__init__(parent)
        uic.loadUi( os.path.splitext(__file__)[0] + '.ui', self )

        self._opExportSlot = opExportSlot
        assert isinstance( opExportSlot, ExportOperatorABC ), \
            "Cannot use {} as an export operator.  "\
            "It doesn't match the required interface".format( type(opExportSlot) )

        # Init child widgets
        self._initMetaInfoWidgets()
        self._initSubregionWidget()
        self._initDtypeConversionWidgets()
        self._initRenormalizationWidgets()
        self._initAxisOrderWidgets()
        self._initFileOptionsWidget()

        # See self.eventFilter()
        self.installEventFilter(self)

    def eventFilter(self, watched, event):
        # Ignore 'enter' keypress events, since the user may just be entering settings.
        # The user must manually click the 'OK' button to close the dialog.
        if watched == self and \
           event.type() == QEvent.KeyPress and \
           ( event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return):
            return True
        return False

    #**************************************************************************
    # Input/Output Meta-info (display only)
    #**************************************************************************
    def _initMetaInfoWidgets(self):
        ## Input/output meta-info display widgets
        opExportSlot = self._opExportSlot
        self.inputMetaInfoWidget.initSlot( opExportSlot.Input )
        self.outputMetaInfoWidget.initSlot( opExportSlot.ImageToExport )

    #**************************************************************************
    # Subregion roi
    #**************************************************************************
    def _initSubregionWidget(self):
        opExportSlot = self._opExportSlot
        inputAxes = opExportSlot.Input.meta.getAxisKeys()

        shape = opExportSlot.Input.meta.shape
        start = (None,) * len( shape )
        stop = (None,) * len( shape )

        if opExportSlot.RegionStart.ready():
            start = opExportSlot.RegionStart.value
        if opExportSlot.RegionStop.ready():
            stop = opExportSlot.RegionStop.value

        self.roiWidget.initWithExtents( inputAxes, shape, start, stop )
        
        def _handleRoiChange(newstart, newstop):
            # Unfortunately, we have to handle a special case here:
            # If the user's previous subregion produced a singleton axis,
            #  then he may have dropped that axis using the 'transpose' edit box.
            # However, if the user is now manipulating the roi again, we need to check to see if that singleton axis was expanded.
            # If it was, then we need to reset the axis order again.  It's no longer valid to drop the axis (it's not a singleton any more.)
            if not opExportSlot.Input.ready():
                # Can happen if we're still listening to slot changes after we've been closed.
                return
            tagged_input_shape = opExportSlot.Input.meta.getTaggedShape()
            tagged_output_shape = opExportSlot.ImageToExport.meta.getTaggedShape()
            missing_axes = set( tagged_input_shape.keys() ) - set( tagged_output_shape.keys() )
            for axis in missing_axes:
                index = tagged_input_shape.keys().index( axis )
                if (stop[index] is None and tagged_input_shape[axis] > 1) \
                or (stop[index] is not None and stop[index] - start[index] > 1):
                    self.axisOrderCheckbox.setChecked(False)
                    break

            # Configure the operator for the new subregion.
            opExportSlot.RegionStart.setValue( newstart )
            opExportSlot.RegionStop.setValue( newstop )

        self.roiWidget.roiChanged.connect( _handleRoiChange )

    #**************************************************************************
    # Dtype conversion
    #**************************************************************************
    def _initDtypeConversionWidgets(self):
        def _selectDefaultDtype():
            dtype = self._opExportSlot.ImageToExport.meta.dtype
            index = self.dtypeCombo.findData( dtype.__name__ )
            self.dtypeCombo.setCurrentIndex( index )
    
        def _handleConvertDtypeChecked():
            checked = self.convertDtypeCheckbox.isChecked()
            self.dtypeCombo.setEnabled( checked )
            if not checked:
                _selectDefaultDtype()

        self.convertDtypeCheckbox.toggled.connect( _handleConvertDtypeChecked )
        dtypes = collections.OrderedDict([ ( "unsigned byte",   "uint8" ),
                                           ( "unsigned 16-bit", "uint16" ),
                                           ( "unsigned 32-bit", "uint32" ),
                                           ( "signed byte",     "int8" ),
                                           ( "signed 16-bit",   "int16" ),
                                           ( "signed 32-bit",   "int32" ),
                                           ( "floating 32-bit", "float32" ),
                                           ( "floating 64-bit", "float64" ) ])
        for name, dtype in dtypes.items():
            self.dtypeCombo.addItem( name, dtype )

        def _handleDtypeSelected():
            # The dtype combo selection changed.  Update the operator to match.
            index = self.dtypeCombo.currentIndex()
            dtype_string = str( self.dtypeCombo.itemData(index).toString() )
            dtype = numpy.dtype(dtype_string).type
            self._opExportSlot.ExportDtype.setValue( dtype )
    
        self.dtypeCombo.currentIndexChanged.connect( _handleDtypeSelected )
        self.dtypeCombo.setEnabled( False )

        # Set the starting setting according to the operator.
        _selectDefaultDtype()
        dtype = self._opExportSlot.ImageToExport.meta.dtype
        if dtype != self._opExportSlot.Input.meta.dtype:
            self.convertDtypeCheckbox.setChecked(True)
            self.dtypeCombo.setEnabled( True )

    #**************************************************************************
    # Renormalization
    #**************************************************************************
    def _initRenormalizationWidgets(self):
        opExportSlot = self._opExportSlot
        dtype = opExportSlot.Input.meta.dtype
        if opExportSlot.InputMax.ready():
            drange = ( opExportSlot.InputMin.value, opExportSlot.InputMax.value )
        else:
            drange = opExportSlot.Input.meta.drange or default_drange( dtype )

        def _handleRangeChange():
            if not self.renormalizeCheckbox.isChecked() or not opExportSlot.Input.ready():
                return
            # Update the operator with the new settings
            input_drange = self.inputValueRange.getValues()
            output_drange = self.outputValueRange.getValues()
            opExportSlot.InputMin.setValue( input_drange[0] )
            opExportSlot.InputMax.setValue( input_drange[1] )
            opExportSlot.ExportMin.setValue( output_drange[0] )
            opExportSlot.ExportMax.setValue( output_drange[1] )

        def _setDefaultInputRange():
            self.inputValueRange.setDType( dtype )
            self.inputValueRange.setLimits( *dtype_limits(dtype) )
            self.inputValueRange.setValues( *drange )

        def _updateOutputRangeForNewDtype(output_dtype):
            self.outputValueRange.setDType( output_dtype )
            self.outputValueRange.setLimits( *dtype_limits( output_dtype ) )
            self.outputValueRange.setValues( *default_drange( output_dtype ) )

        def _handleRenormalizeChecked( checked ):
            self.inputValueRange.setEnabled( checked )
            self.outputValueRange.setEnabled( checked )
            if checked:
                output_dtype = opExportSlot.ImageToExport.meta.dtype
                _setDefaultInputRange()
                _updateOutputRangeForNewDtype(output_dtype)
                _handleRangeChange()
            else:
                # Clear the gui
                self.inputValueRange.setBlank()
                self.outputValueRange.setBlank()
                # Clear the operator slots
                opExportSlot.InputMin.disconnect()
                opExportSlot.InputMax.disconnect()
                opExportSlot.ExportMin.disconnect()
                opExportSlot.ExportMax.disconnect()

        # Init gui with default values
        _updateOutputRangeForNewDtype( opExportSlot.ImageToExport.meta.dtype )
            
        # Update gui with settings from the operator (if any)
        if opExportSlot.InputMax.ready():
            self.renormalizeCheckbox.setChecked( True )
            self.inputValueRange.setEnabled( True )
            self.outputValueRange.setEnabled( True )
            self.inputValueRange.setValues( *drange )
        else:
            self.renormalizeCheckbox.setChecked( False )
            self.inputValueRange.setEnabled( False )
            self.outputValueRange.setEnabled( False )
        
        if opExportSlot.ExportMax.ready():
            self.outputValueRange.setValues( opExportSlot.ExportMin.value, opExportSlot.ExportMax.value )

        # Subscribe to user changes
        self.inputValueRange.changedSignal.connect( _handleRangeChange )
        self.outputValueRange.changedSignal.connect( _handleRangeChange )
        self.renormalizeCheckbox.toggled.connect( _handleRenormalizeChecked )

        def _handleOutputDtypeChange(*args):
            """
            The output slot dtype changed.
            Update the normalization gui controls with the appropriate limits.
            """
            output_dtype = self._opExportSlot.ImageToExport.meta.dtype
            if output_dtype != self.outputValueRange.dtype and self.renormalizeCheckbox.isChecked():
                _updateOutputRangeForNewDtype(output_dtype)

        # Update the output range widget whenever the output dtype changes.
        opExportSlot.ImageToExport.notifyMetaChanged( _handleOutputDtypeChange )

    #**************************************************************************
    # Axis order
    #**************************************************************************
    def _initAxisOrderWidgets(self):
        if self._opExportSlot.OutputAxisOrder.ready():
            self.axisOrderCheckbox.setChecked( Qt.Checked )
            self.outputAxisOrderEdit.setText( self._opExportSlot.OutputAxisOrder.value )
            
        def _handleNewAxisOrder():
            new_order = str( self.outputAxisOrderEdit.text() )
            validator_state, _ = self.outputAxisOrderEdit.validator().validate( new_order, 0 )
            if validator_state == QValidator.Acceptable:
                self._opExportSlot.OutputAxisOrder.setValue( new_order )

        def _handleAxisOrderChecked( checked ):
            self.outputAxisOrderEdit.setEnabled( checked )
            default_order = "".join( self._opExportSlot.Input.meta.getAxisKeys() )
            self.outputAxisOrderEdit.setText( default_order )
            if checked:
                _handleNewAxisOrder()
            else:
                self._opExportSlot.OutputAxisOrder.disconnect()
                self._updateAxisOrderColor(False)
        
        self.outputAxisOrderEdit.editingFinished.connect( _handleNewAxisOrder )
        self.outputAxisOrderEdit.textChanged.connect( partial(self._updateAxisOrderColor, True) )
        self.outputAxisOrderEdit.setValidator( DataExportOptionsDlg._AxisOrderValidator( self, self._opExportSlot.ConvertedImage ) )
        self.outputAxisOrderEdit.installEventFilter( DataExportOptionsDlg._AxisOrderEventFilter(self) )
        self.axisOrderCheckbox.toggled.connect( _handleAxisOrderChecked )

    def _updateAxisOrderColor(self, allow_intermediate):
        checked = self.axisOrderCheckbox.isChecked()
        text = self.outputAxisOrderEdit.text()
        state, _ = self.outputAxisOrderEdit.validator().validate( text, 0 )
        invalidAxes = (checked and state != QValidator.Acceptable and not allow_intermediate)
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled( not invalidAxes )
        if invalidAxes:
            self.outputAxisOrderEdit.setStyleSheet("QLineEdit {background-color: red}" )
        else:
            self.outputAxisOrderEdit.setStyleSheet("QLineEdit {background-color: white}" )

    class _AxisOrderEventFilter(QObject):
        def __init__(self, parent):
            super( DataExportOptionsDlg._AxisOrderEventFilter, self ).__init__(parent)

        def eventFilter(self, watched, event):
            # Watch for focus-out events and 'enter' keypresses
            if event.type() == QEvent.FocusOut or \
               ( event.type() == QEvent.KeyPress and \
                 ( event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return) ):
                self.parent()._updateAxisOrderColor( allow_intermediate=False )    
            return False

    class _AxisOrderValidator(QValidator):
        def __init__(self, parent, inputSlot):
            super( DataExportOptionsDlg._AxisOrderValidator, self ).__init__(parent)
            self._inputSlot = inputSlot
        
        def validate(self, userAxes, pos):
            taggedShape = self._inputSlot.meta.getTaggedShape()
            inputAxes = taggedShape.keys()
            inputSet = set(inputAxes)
            userSet = set(str(userAxes))
            
            # Ensure all user axes appear in the input
            if not (userSet <= inputSet):
                return (QValidator.Invalid, pos)
            
            # Ensure no repeats
            if len(userSet) != len(userAxes):
                return (QValidator.Invalid, pos)
            
            # If missing non-singleton axes, maybe intermediate entry
            # (It's okay to omit singleton axes)
            for key in (inputSet - userSet):
                if taggedShape[key] != 1:
                    return (QValidator.Intermediate, pos)
            
            return (QValidator.Acceptable, pos)

    #**************************************************************************
    # File format and options
    #**************************************************************************
    def _initFileOptionsWidget(self):
        opExportSlot = self._opExportSlot
        self.exportFileOptionsWidget.initExportOp( opExportSlot )
        
#**************************************************************************
# Helper functions
#**************************************************************************
def default_drange(dtype):
    if numpy.issubdtype(dtype, numpy.integer):
        return dtype_limits(dtype)
    if numpy.issubdtype(dtype, numpy.floating):
        return (0.0, 1.0)
    raise RuntimeError( "Unknown dtype: {}".format( dtype ) )

def dtype_limits(dtype):
    if numpy.issubdtype(dtype, numpy.integer):
        return (numpy.iinfo(dtype).min, numpy.iinfo(dtype).max)
    if numpy.issubdtype(dtype, numpy.floating):
        return (numpy.finfo(dtype).min, numpy.finfo(dtype).max)
    raise RuntimeError( "Unknown dtype: {}".format( dtype ) )

#**************************************************************************
# Quick debug
#**************************************************************************
if __name__ == "__main__":
    import vigra
    from PyQt4.QtGui import QApplication
    from lazyflow.graph import Graph
    from lazyflow.operators.ioOperators import OpFormattedDataExport

    data = numpy.zeros( (10,20,30,3), dtype=numpy.float32 )
    data = vigra.taggedView(data, 'zyxc')

    op = OpFormattedDataExport( graph=Graph() )
    op.Input.setValue( data )

    app = QApplication([])
    w = DataExportOptionsDlg(None, op)
    w.show()
    
    app.exec_()












