"""oiv bouwlaag control widget"""
import os

import qgis.PyQt as PQt #pylint: disable=import-error
import qgis.PyQt.QtCore as PQtC #pylint: disable=import-error
import qgis.PyQt.QtWidgets as PQtW #pylint: disable=import-error
import qgis.core as QC #pylint: disable=import-error

import oiv.tools.utils_core as UC
import oiv.tools.utils_gui as UG
import oiv.plugin_helpers.drawing_helper as DW
import oiv.plugin_helpers.messages as MSG
import oiv.plugin_helpers.configdb_helper as CH
import oiv.plugin_helpers.plugin_constants as PC

FORM_CLASS, _ = PQt.uic.loadUiType(os.path.join(
    os.path.dirname(__file__), PC.PAND["bouwlaagui"]))

class oivBouwlaagWidget(PQtW.QDockWidget, FORM_CLASS):
    """create bouwlaag from BAG, copy or draw"""

    canvas = None
    iface = None
    layer = None
    objectId = None
    bouwlaagList = []
    snapLayerNames = DW.BLSNAPLAYERS
    parent = None

    def __init__(self, parent):
        """initialize dockwidget and connect slots and signals"""
        super(oivBouwlaagWidget, self).__init__(parent)
        self.setupUi(self)
        self.parent = parent
        self.objectId = self.parent.pand_id.text()
        self.bouwlaag_bag.clicked.connect(self.run_bag_overnemen)
        self.bouwlaag_tekenen.clicked.connect(self.run_bouwlaag_tekenen)
        self.bouwlaag_overnemen.clicked.connect(self.run_bouwlaag_overnemen)
        self.terug.clicked.connect(self.close_bouwlaag)
        self.copy.clicked.connect(self.run_select_bouwlaag)
        self.label1.setVisible(False)
        self.label2.setVisible(False)
        self.label3.setVisible(False)
        UG.set_lengte_oppervlakte_visibility(self, False, False, False, False)
        self.bouwlaag_max.setVisible(False)
        self.bouwlaag.setVisible(False)
        self.copy.setVisible(False)
        for var in vars(self):
            typeVar = type(vars(self)[var])
            if typeVar == PQtW.QCheckBox:
                vars(self)[var].setVisible(False)

    def run_bag_overnemen(self):
        """copy polygon of bag feature"""
        UG.set_lengte_oppervlakte_visibility(self, False, False, False, False)
        layerName = PC.PAND["bagpandlayername"]
        ilayer = UC.getlayer_byname(layerName)
        request = QC.QgsFeatureRequest().setFilterExpression('"identificatie" = ' + "'{}'".format(self.objectId))
        ifeature = next(ilayer.getFeatures(request))
        self.copy_bag_bouwlaag(ilayer, ifeature)

    def run_bouwlaag_overnemen(self):
        """copy floor from another floor"""
        UG.set_lengte_oppervlakte_visibility(self, False, False, False, False)
        self.label1.setVisible(True)
        self.label2.setVisible(True)
        self.label3.setVisible(True)
        self.bouwlaag.setVisible(True)
        for var in vars(self):
            typeVar = type(vars(self)[var])
            if typeVar == PQtW.QCheckBox:
                vars(self)[var].setVisible(True)
        #append combobox with unique existing floors
        self.bouwlagen_to_combobox()
        self.copy.setVisible(True)
        #connect signal to slot
        self.bouwlaag.currentIndexChanged.connect(self.set_layer_subset_bouwlaag)
        self.parent.selectTool.geomSelected.connect(self.copy_bag_bouwlaag)

    def run_bouwlaag_tekenen(self):
        """draw a floor with the basic functionality of QGIS"""
        drawTool = self.parent.drawTool
        possibleSnapFeatures = UC.get_possible_snapFeatures_bouwlaag(self.snapLayerNames, self.objectId)
        layer = UC.getlayer_byname(PC.PAND["bouwlaaglayername"])
        drawTool.layer = layer
        drawTool.possibleSnapFeatures = possibleSnapFeatures
        drawTool.canvas = self.canvas
        drawTool.onGeometryAdded = self.draw_feature
        drawTool.captureMode = 2
        self.canvas.setMapTool(drawTool)
        UG.set_lengte_oppervlakte_visibility(self, True, True, True, True)
        drawTool.parent = self

    def run_select_bouwlaag(self):
        """set selecttool as maptool"""
        self.canvas.setMapTool(self.parent.selectTool)

    def set_layer_subset_bouwlaag(self):
        """set layers substring which are a childlayer of "bouwlagen"""
        comboboxText = str(self.bouwlaag.currentText())
        if comboboxText != "":
            sub_string = "bouwlaag = " + str(self.bouwlaag.currentText())
            UG.set_layer_substring(sub_string)

    def copy_layers(self, parentID, newID, layer, bouwlaag):
        """select the features"""
        fields = layer.fields()
        newFeature = QC.QgsFeature()
        newFeature.initAttributes(fields.count())
        newFeature.setFields(fields)
        attrs = CH.get_allkeys_bl(layer.name())
        #get features by bouwlaag ID
        it = layer.getFeatures(QC.QgsFeatureRequest().setFilterExpression(attrs[0] + '=' + str(parentID)))
        for feat in it:
            newFeature.setGeometry(feat.geometry())
            if attrs[1]:
                if str(feat[attrs[1]]).isdigit():
                    newFeature[attrs[1]] = int(feat[attrs[1]])
                else:
                    newFeature[attrs[1]] = feat[attrs[1]]
            if attrs[2]:
                newFeature[attrs[2]] = feat[attrs[2]]
            if attrs[3]:
                newFeature[attrs[3]] = feat[attrs[3]]
            newFeature[attrs[0]] = int(newID)
            newFeature["bouwlaag"] = bouwlaag
            UC.write_layer(layer, newFeature)

    def copy_selected_layers(self, ifeature, newFeatureId, bouwlaag):
        """copy related selected features"""
        bouwlaagID = ifeature["id"]
        for var in vars(self):
            typeVar = type(vars(self)[var])
            if typeVar == PQtW.QCheckBox:
                if vars(self)[var].isChecked():
                    copyLayer = UC.getlayer_byname(vars(self)[var].text())
                    self.copy_layers(bouwlaagID, newFeatureId, copyLayer, bouwlaag) 

    def draw_feature(self, points, _dummy):
        """create the floor feature and save to the floors layer"""
        minBouwlaag = int(self.bouwlaag_min.text())
        maxBouwlaag = int(self.bouwlaag_max.text())
        childFeature = QC.QgsFeature()
        layerName = PC.PAND["bouwlaaglayername"]
        layer = UC.getlayer_byname(layerName)
        foreignKey = CH.get_foreign_key_bl(layerName)
        #construct QgsFeature to save
        for i in range(minBouwlaag, maxBouwlaag + 1):
            if i != 0:
                childFeature.setGeometry(QC.QgsGeometry.fromPolygonXY([points]))
                fields = layer.fields()
                childFeature.initAttributes(fields.count())
                childFeature.setFields(fields)
                childFeature[foreignKey] = self.objectId
                childFeature["bouwlaag"] = i
                UC.write_layer(layer, childFeature)
                #block the signals of changing the comboBox to add the new floor
                self.bouwlaag.blockSignals(True)
                self.bouwlaag.clear()
                if i not in self.bouwlaagList:
                    self.bouwlaagList.append(i)
        self.bouwlaagList.sort()
        self.bouwlagen_to_combobox()
        self.bouwlaag.blockSignals(False)
        self.iface.actionPan().trigger()
        #set all layers substring to the right floor
        sub_string = "bouwlaag = " + str(minBouwlaag)
        UG.set_layer_substring(sub_string)
        if maxBouwlaag != minBouwlaag:
            MSG.showMsgBox('bouwlaagcreated')

    def copy_bag_bouwlaag(self, ilayer, ifeature):
        """copy the floor drom the BAG features"""
        if ilayer.name() == PC.PAND["bouwlaaglayername"] or ilayer.name() == PC.PAND["bagpandlayername"]:
            childFeature = QC.QgsFeature()
            layerName = PC.PAND["bouwlaaglayername"]
            #get active floor from dockwidget
            minBouwlaag = int(self.bouwlaag_min.text())
            maxBouwlaag = int(self.bouwlaag_max.text())
            layer = UC.getlayer_byname(layerName)
            #get necessary attributes from config file
            foreignKey = CH.get_foreign_key_bl(layerName)
            #construct QgsFeature to save
            for i in range(minBouwlaag, maxBouwlaag + 1):
                if i != 0:
                    childFeature.setGeometry(ifeature.geometry())
                    fields = layer.fields()
                    childFeature.initAttributes(fields.count())
                    childFeature.setFields(fields)
                    childFeature[foreignKey] = self.objectId
                    childFeature["bouwlaag"] = i
                    newFeatureId = UC.write_layer(layer, childFeature)
                    #copy also the selected layers
                    if ilayer.name() == PC.PAND["bouwlaaglayername"]:
                        self.copy_selected_layers(ifeature, newFeatureId, i)
                    #block the signals of changing the comboBox to add the new floor
                    self.bouwlaag.blockSignals(True)
                    self.bouwlaag.clear()
                    if i not in self.bouwlaagList:
                        self.bouwlaagList.append(i)
            self.bouwlaagList.sort()
            self.bouwlagen_to_combobox()
            self.bouwlaag.blockSignals(False)
            self.iface.actionPan().trigger()
            #set all layers substring to the right floor
            sub_string = "bouwlaag = " + str(minBouwlaag)
            UG.set_layer_substring(sub_string)
            try:
                self.parent.selectTool.geomSelected.disconnect()
            except:  # pylint: disable=bare-except
                pass
            if maxBouwlaag >= minBouwlaag:
                MSG.showMsgBox('bouwlaagcreated')
        else:
            MSG.showMsgBox('nobouwlaagselected')
            try:
                self.parent.selectTool.geomSelected.disconnect()
            except:  # pylint: disable=bare-except
                pass
            self.parent.selectTool.geomSelected.connect(self.copy_bag_bouwlaag)

    def bouwlagen_to_combobox(self):
        """add existing floors to the comboBox of the "bouwlaagdockwidget"""
        self.bouwlaag.blockSignals(True)
        self.bouwlaag.clear()
        for i in range(len(self.bouwlaagList) + 1):
            if i == 0:
                self.bouwlaag.addItem("")
            else:
                self.bouwlaag.addItem(str(self.bouwlaagList[i - 1]))
        self.bouwlaag.blockSignals(False)
        index = self.bouwlaag.findText(str(self.bouwlaag_min.text()), PQtC.Qt.MatchFixedString)
        if index >= 0:
            self.bouwlaag.setCurrentIndex(index)
        else:
            self.bouwlaag.setCurrentIndex(0)

    def close_bouwlaag(self):
        """close floor widget and return to main menu"""
        self.label1.setVisible(False)
        self.label2.setVisible(False)
        self.label3.setVisible(False)
        self.bouwlaag.setVisible(False)
        self.copy.setVisible(False)
        for var in vars(self):
            typeVar = type(vars(self)[var])
            if typeVar == PQtW.QCheckBox:
                vars(self)[var].setVisible(False)
        self.parent.sortedList = self.bouwlaagList
        self.parent.bouwlagen_to_combobox(self.objectId, int(self.bouwlaag_min.text()))
        self.parent.show()
        self.close()
        try:
            del self.parent
        except:  # pylint: disable=bare-except
            pass
        del self
