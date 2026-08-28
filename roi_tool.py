# -*- coding: utf-8 -*-
# Created by Miguel Alexandre da Cunha
from qgis.core import (
    QgsWkbTypes,
    QgsCoordinateTransform,
    QgsProject,
    QgsCoordinateReferenceSystem,
    QgsPointXY,
)
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.PyQt.QtGui import QColor

class RoiDrawTool(QgsMapTool):
    """Ferramenta simples de digitalização de polígono no canvas do QGIS.

    Clique com o botão esquerdo para adicionar vértices, clique com o botão
    direito (ou tecle Enter) para finalizar o polígono. Emite `finished`
    com a lista de vértices em coordenadas geográficas (lon, lat / WGS84)."""

    finished = pyqtSignal(list)
    cancelled = pyqtSignal()

    def __init__(self, canvas):
        super().__init__(canvas)
        self.canvas = canvas
        self.points = []
        self.rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubber_band.setColor(QColor(111, 184, 151, 80))
        self.rubber_band.setStrokeColor(QColor(95, 166, 134, 230))
        self.rubber_band.setWidth(2)

    def canvasPressEvent(self, event):
        if event.button() == Qt.RightButton:
            self._finish()
            return
        point = self.toMapCoordinates(event.pos())
        self.points.append(point)
        self._update_band()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._finish()
        elif event.key() == Qt.Key_Escape:
            self.points = []
            self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
            self.cancelled.emit()

    def _update_band(self):
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        for pt in self.points:
            self.rubber_band.addPoint(pt, True)

    def _finish(self):
        if len(self.points) < 3:
            self.cancelled.emit()
            self.points = []
            self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
            return

        canvas_crs = self.canvas.mapSettings().destinationCrs()
        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        xform = QgsCoordinateTransform(canvas_crs, wgs84, QgsProject.instance())

        coords = []
        for pt in self.points:
            geo_pt = xform.transform(pt) if canvas_crs != wgs84 else pt
            coords.append((geo_pt.x(), geo_pt.y()))

        self.points = []
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        self.finished.emit(coords)

    def deactivate(self):
        self.points = []
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        super().deactivate()
