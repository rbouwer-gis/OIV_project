"""control pand to draw upon"""
import os
import webbrowser

import qgis.PyQt as PQt #pylint: disable=import-error
import qgis.PyQt.QtCore as PQtC #pylint: disable=import-error
import qgis.PyQt.QtWidgets as PQtW #pylint: disable=import-error
import qgis.core as QC #pylint: disable=import-error

import oiv.tools.utils_core as UC
import oiv.tools.utils_gui as UG
import oiv.tools.query_bag as QB
import oiv.tools.stackwidget as SW
import oiv.plugin_helpers.messages as MSG
import oiv.plugin_helpers.configdb_helper as CH
import oiv.plugin_helpers.qt_helper as QH
import oiv.plugin_helpers.plugin_constants as PC

from .oiv_bouwlaag import oivBouwlaagWidget
from .oiv_tekenen import oivTekenWidget
from .oiv_import_file import oivImportFileWidget

FORM_CLASS, _ = PQt.uic.loadUiType(os.path.join(
    os.path.dirname(__file__), PC.PAND["pandui"]))

class oivPandWidget(PQtW.QDockWidget, FORM_CLASS):

    iface = None
    canvas = None
    basewidget = None
    selectTool = None
    pointTool = None
    sortedList = []
    attributeform = None
    objectFeature = None
    drawTool = None
    moveTool = None
    identifyTool = None
    minBouwlaag = 0
    maxBouwlaag = 0

    def __init__(self, parent=None):
        super(oivPandWidget, self).__init__(parent)
        self.setupUi(self)

    def initUI(self):
        """fill the lineedits with values"""
        #Get the related BAG attributes from BAG API
        ilayer = UC.getlayer_byname('BAG panden')
        foreignKey = 'identificatie'
        objectId = self.pand_id.text()
        request = QC.QgsFeatureRequest().setFilterExpression(foreignKey + " = '" + objectId + "'")
        tempFeature = next(ilayer.getFeatures(request))
        bagGebruiksdoel = str(tempFeature['gebruiksdoel'])
        if self.adres_1.text() == "":
            bagAdres1, bagAdres2, bagGebruiksdoel = QB.ask_bag_adress(objectId, bagGebruiksdoel)
            self.adres_1.setText(bagAdres1)
            self.adres_2.setText(bagAdres2)
            self.gebruiksdoel.setText(bagGebruiksdoel)
        self.bouwlagen_to_combobox(objectId, None)

    def initActions(self):
        """connect the buttons to their actions"""
        self.bouwlaag_toevoegen.clicked.connect(self.run_bouwlaag)
        self.tekenen.clicked.connect(self.run_tekenen)
        self.comboBox.currentIndexChanged.connect(self.set_layer_subset_bouwlaag)
        self.bouwlaag_bewerken.clicked.connect(self.run_bouwlaag_bewerken)
        self.import_2.clicked.connect(self.run_import)
        self.terug.clicked.connect(self.close_object_show_base)
        self.terugmelden.clicked.connect(self.openBagviewer)
        self.delete_f.clicked.connect(self.run_delete)

    def run_edit_bouwlagen(self, ilayer, ifeature):
        """edit attribute form of floor feature"""
        stackWidget = SW.oivStackWidget()
        self.iface.addDockWidget(QH.getWidgetType(), stackWidget)
        stackWidget.update()
        stackWidget.parentWidget = self
        stackWidget.open_feature_form(ilayer, ifeature)
        self.close()
        stackWidget.show()

    def bouwlagen_to_combobox(self, objectId, actieveBouwlaag):
        """fill combobox with existing floors"""
        runLayer = PC.PAND["bouwlaaglayername"]
        tempLayer = UC.getlayer_byname(runLayer)
        objectId = self.pand_id.text()
        foreignKey = CH.get_foreign_key_bl(runLayer)
        tempLayer.setSubsetString('')
        #request all existing floors of object feature
        request = QC.QgsFeatureRequest().setFilterExpression(foreignKey + " = '" + str(objectId) + "'")
        tempFeatureIt = tempLayer.getFeatures(request)
        #create unique list of existing floors and sort it from small to big
        bouwlaagList = [it["bouwlaag"] for it in tempFeatureIt]
        self.sortedList = UC.create_unique_sorted_list(bouwlaagList)
        #block signal of combobox to add existing floors
        self.comboBox.blockSignals(True)
        self.comboBox.clear()
        for bouwlaag in reversed(self.sortedList):
            self.comboBox.addItem(str(bouwlaag))
        #if there are existing floors "tekenen" can be enabled
        if self.sortedList:
            self.tekenen.setEnabled(True)
            if actieveBouwlaag is None:
                actieveBouwlaag = min(reversed(self.sortedList), key=abs)
        else:
            self.tekenen.setEnabled(False)
            actieveBouwlaag = 1
        self.comboBox.blockSignals(False)
        #set substring of childlayers
        subString = "bouwlaag = " + str(actieveBouwlaag)
        UG.set_layer_substring(subString)
        index = self.comboBox.findText(str(actieveBouwlaag), PQtC.Qt.MatchFixedString)
        if index >= 0:
            self.comboBox.setCurrentIndex(index)
        self.iface.actionPan().trigger()

    def set_layer_subset_bouwlaag(self):
        """if index of combobox has changed set cql filter of childlayers"""
        subString = "bouwlaag = " + str(self.comboBox.currentText())
        UG.set_layer_substring(subString)

    #select bouwlaag on canvas to edit the atrribute form
    def run_bouwlaag_bewerken(self):
        runLayer = PC.PAND["bouwlaaglayername"]
        ilayer = UC.getlayer_byname(runLayer)
        objectId = self.pand_id.text()
        foreignKey = CH.get_foreign_key_bl(runLayer)
        request = QC.QgsFeatureRequest().setFilterExpression(foreignKey + " = '" + str(objectId) + "'")
        ifeature = next(ilayer.getFeatures(request))
        self.run_edit_bouwlagen(ilayer, ifeature)

    #add new floor
    def run_bouwlaag(self):
        while True:
            bouwlaag, bouwlaagMax, ok = BouwlaagDialog.getBouwlagen()
            if (bouwlaag != 0 and bouwlaagMax >= bouwlaag and ok is True):
                self.close()
                bouwlaagwidget = oivBouwlaagWidget(self)
                self.iface.addDockWidget(QH.getWidgetType(), bouwlaagwidget)
                bouwlaagwidget.canvas = self.canvas
                bouwlaagwidget.iface = self.iface
                bouwlaagwidget.bouwlaagList = self.sortedList
                bouwlaagwidget.teken_bouwlaag.setText(str(bouwlaag) + ' t/m ' + str(bouwlaagMax))
                bouwlaagwidget.bouwlaag_min.setText(str(bouwlaag))
                bouwlaagwidget.bouwlaag_max.setText(str(bouwlaagMax))
                bouwlaagwidget.teken_bouwlaag.setEnabled(False)
                subString = "bouwlaag = " + str(bouwlaag)
                UG.set_layer_substring(subString)
                bouwlaagwidget.show()
                break
            elif bouwlaagMax < bouwlaag:
                MSG.showMsgBox('bouwlaagvolgorde')
            elif ok is False:
                break

    def run_tekenen(self):
        """init teken widget"""
        tekenwidget = oivTekenWidget(self)
        subString = "bouwlaag = " + str(self.comboBox.currentText())
        UG.set_layer_substring(subString)
        self.iface.addDockWidget(PQtC.Qt.RightDockWidgetArea, tekenwidget)
        self.close()
        tekenwidget.show()

    def openBagviewer(self):
        """open url based on BAG pand_id, i.v.m. terugmelden"""
        url = PC.PAND["bagviewerurl"] + str(self.pand_id.text())
        webbrowser.open(url)

    def run_delete(self):
        layerName = PC.PAND["bouwlaaglayername"]
        ilayer = UC.getlayer_byname(layerName)
        self.iface.setActiveLayer(ilayer)
        objectId = self.pand_id.text()
        request = QC.QgsFeatureRequest().setFilterExpression('"pand_id" = ' + "'{}'".format(objectId))
        ifeature = next(ilayer.getFeatures(request))
        ilayer.startEditing()
        ilayer.selectByIds([ifeature.id()])
        reply = MSG.showMsgBox('deleteobject')
        if not reply:
            #als "nee" deselecteer alle geselecteerde features
            ilayer.setSelectedFeatures([])
        elif reply:
            #als "ja" -> verwijder de feature op basis van het unieke feature id
            ilayer.deleteFeature(ifeature.id())
            ilayer.commitChanges()
            reply = MSG.showMsgBox('deletedobject')
            UC.refresh_layers(self.iface)
            #set actieve bouwlaag to 1 and fill combobox
            self.bouwlagen_to_combobox(ifeature.id(), 1)

    def run_import(self):
        """initiate import widget"""
        importwidget = oivImportFileWidget(self)
        self.iface.addDockWidget(QH.getWidgetType(), importwidget)
        self.close()
        importwidget.show()

    def close_object_show_base(self):
        subString = "bouwlaag = 1"
        UG.set_layer_substring(subString)
        for widget in self.children():
            if isinstance(widget, PQtW.QPushButton):
                try:
                    widget.clicked.disconnect()
                except: # pylint: disable=bare-except
                    pass
        self.close()
        self.basewidget.show()
        self.iface.actionPan().trigger()
        del self

class BouwlaagDialog(PQtW.QDialog):
    def __init__(self, parent = None):
        super(BouwlaagDialog, self).__init__(parent)
        maxBouwlaag = 30
        minBouwlaag = -10
        self.setWindowTitle("Bouwlagen toevoegen")
        qlayout = PQtW.QVBoxLayout(self)
        self.qlineA = PQtW.QLabel(self)
        self.qlineB = PQtW.QLabel(self)
        self.qlineC = PQtW.QLabel(self)
        self.qComboA = PQtW.QComboBox(self)
        self.qComboB = PQtW.QComboBox(self)
        self.qlineA.setText("U kunt meerdere bouwlagenlagen in 1x creeren, door van en t/m in te vullen!")
        self.qlineB.setText("Van:")
        self.qlineC.setText("Tot en met:")
        for i in range(maxBouwlaag - minBouwlaag + 1):
            if maxBouwlaag - i != 0:
                self.qComboA.addItem(str(maxBouwlaag - i))
                self.qComboB.addItem(str(maxBouwlaag - i))
                if maxBouwlaag - i == 1:
                    init_index = i
        self.qComboA.setCurrentIndex(init_index) 
        self.qComboB.setCurrentIndex(init_index)  
        self.qComboA.setFixedWidth(100)
        self.qComboA.setMaxVisibleItems(30)
        self.qComboB.setFixedWidth(100)
        self.qComboB.setMaxVisibleItems(30) 
        self.qComboA.currentIndexChanged.connect(self.set_comboboxB)
        qlayout.addWidget(self.qlineA)
        qlayout.addWidget(self.qlineB)
        qlayout.addWidget(self.qComboA)
        qlayout.addWidget(self.qlineC)
        qlayout.addWidget(self.qComboB)
        buttons = PQtW.QDialogButtonBox(
            PQtW.QDialogButtonBox.Ok | PQtW.QDialogButtonBox.Cancel,
            PQtC.Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        qlayout.addWidget(buttons)

    def set_comboboxB(self):
        ind = self.qComboA.currentIndex()
        self.qComboB.setCurrentIndex(ind)

    @staticmethod
    def getBouwlagen(parent=None):
        dialog = BouwlaagDialog(parent)
        result = dialog.exec_()
        return (int(dialog.qComboA.currentText()), int(dialog.qComboB.currentText()), result == PQtW.QDialog.Accepted)
