# encoding: utf-8

from __future__ import division, print_function, unicode_literals
import objc
from AppKit import NSBeep, NSBundle, NSColor, NSBezierPath, NSPoint, NSRect
from GlyphsApp import Glyphs, addPoints
from GlyphsApp.plugins import SelectTool


def get_intersection(x1, y1, x2, y2, x3, y3, x4, y4):
	px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / ((x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4))
	py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / ((x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4))
	return px, py


def derivative(p0, p1, p2, p3, t):
	return 3 * ((1 - t)**2) * (p1 - p0) + 6 * (1 - t) * t * (p2 - p1) + 3 * (t**2) * (p3 - p2)


def second_derivative(p0, p1, p2, p3, t):
	return 6 * (1 - t) * (p2 - 2 * p1 + p0) + 6 * t * (p3 - 2 * p2 + p1)


def curvature(x0, y0, x1, y1, x2, y2, x3, y3, t):
	dx = derivative(x0, x1, x2, x3, t)
	ddx = second_derivative(x0, x1, x2, x3, t)
	dy = derivative(y0, y1, y2, y3, t)
	ddy = second_derivative(y0, y1, y2, y3, t)
	return (ddx * dy - ddy * dx) / ((dy ** 2 + dx ** 2) ** 1.5)


def y2_from_k(x0, y0, x1, y1, x2, _, x3, y3, k):
	return ((((x1 - x0)**2 + (y1 - y0)**2)**1.5) * k * 3 / 2 + x0 * y1 - x1 * y0 + x2 * y0 - x2 * y1) / (x0 - x1)


def x_2_from_k(x0, y0, x1, y1, _, __, x3, y3, k, z, b):
	return ((((x1 - x0)**2 + (y1 - y0)**2)**1.5) * k * 3 / 2 - b * x0 + b * x1 + x0 * y1 - x1 * y0) / (x0 * z - x1 * z - y0 + y1)


def y1_from_k(x0, y0, x1, _, x2, y2, x3, y3, k):
	return ((((x3 - x2)**2 + (y3 - y2)**2)**1.5) * 3 * k / 2 + x1 * y2 - x1 * y3 + x2 * y3 - x3 * y2) / (x2 - x3)


def x1_from_k(x0, y0, _, __, x2, y2, x3, y3, k, z, b):
	return ((((x3 - x2)**2 + (y3 - y2)**2)**1.5) * 3 * k / 2 - b * x2 + b * x3 + x2 * y3 - x3 * y2) / (x2 * z - x3 * z - y2 + y3)


def get_line_params(x0, y0, x1, y1):
	if x0 - x1 != 0:
		z = (y0 - y1) / (x0 - x1)
	else:
		z = 0
	b = (y0 + y1 - z * (x0 + x1)) / 2
	return z, b


def find_selected_offcurve_node(layer):
	if len(layer.selection) != 1:
		return

	for shape in layer.shapes:
		if not hasattr(shape, 'nodes'):
			continue
		if not shape.nodes:
			continue
		for node in shape.nodes:
			if node in layer.selection and node.type == 'offcurve':
				N = node.nextNode
				P = node.prevNode
				if is_p1(node, N, P) or is_p2(node, N, P):
					return node


def unpack_node(node):
	N = node.nextNode
	NN = N.nextNode if N else None
	P = node.prevNode
	PP = P.prevNode if P else None
	return N, NN, P, PP


def unpack_coords(node):
	N, NN, P, PP = unpack_node(node)
	if is_p1(node, N, P):
		return P.x, P.y, node.x, node.y, N.x, N.y, NN.x, NN.y
	elif is_p2(node, N, P):
		return PP.x, PP.y, P.x, P.y, node.x, node.y, N.x, N.y


def is_p1(node, N, P):
	return node.type == 'offcurve' and N.type == 'offcurve'


def is_p2(node, N, P):
	return node.type == 'offcurve' and P.type == 'offcurve'


def initial_curvature(selected_node):
	N, NN, P, PP = unpack_node(selected_node)
	coords = unpack_coords(selected_node)
	if is_p1(selected_node, N, P):
		return curvature(*coords, 0)
	elif is_p2(selected_node, N, P):
		return curvature(*coords, 1)
	else:
		return None


def projection(A, B, point):
	t = ((point.x - A.x) * (B.x - A.x) + (point.y - A.y) * (B.y - A.y)) / (pow((B.x - A.x), 2) + pow((B.y - A.y), 2))
	p_x = A.x + t * (B.x - A.x)
	p_y = A.y + t * (B.y - A.y)
	return NSPoint(p_x, p_y)


toolbarIcon = None

class HarmonicMove(SelectTool):
	icon = None
	initial_dragging_k = None

	@classmethod
	def initialize(cls):
		global toolbarIcon
		bundle = NSBundle.bundleWithIdentifier_('com.pkolchanov.HarmonicMove')
		toolbarIcon = bundle.imageForResource_('HarmonicMoveToolbar')
		toolbarIcon.setTemplate_(True)
		toolbarIcon.setName_('HarmonicMoveToolbar')
		highlightIcon = bundle.imageForResource_('HarmonicMoveToolbarHighlight')
		highlightIcon.setTemplate_(True)
		highlightIcon.setName_('HarmonicMoveToolbarHighlight')

	def toolBarIcon(self):
		return toolbarIcon

	@objc.python_method
	def settings(self):
		self.name = Glyphs.localize({'en': u'Harmonic Move'})
		self.keyboardShortcut = 'm'
		self.toolbarPosition = 50

	@objc.python_method
	def start(self):
		pass

	@objc.python_method
	def activate(self):
		pass

	@objc.python_method
	def background(self, layer):
		node = find_selected_offcurve_node(layer)
		if not node:
			return

		intersection = NSPoint(*get_intersection(
			*unpack_coords(node)
		))

		if intersection:
			handSizeInPoints = 1 + Glyphs.handleSize * 2.5  # (= 5.0 or 7.5 or 10.0)
			handleSize = handSizeInPoints / Glyphs.font.currentTab.scale

			NSColor.redColor().set()
			rect = NSRect(
				intersection.x - handleSize / 2,
				intersection.y - handleSize / 2,
				handleSize,
				handleSize
			)
			NSBezierPath.bezierPathWithOvalInRect_(rect).fill()



	@objc.python_method
	def deactivate(self):
		pass

	def setDragging_(self, ds):
		objc.super(HarmonicMove, self).setDragging_(ds)
		if ds:
			layer = self.editViewController().graphicView().activeLayer()
			node = find_selected_offcurve_node(layer)
			if not node:
				return
			self.initial_dragging_k = initial_curvature(node)


	def moveSelectionWithPoint_withModifier_(self, delta, modidierKeys):
		alt_pressed = modidierKeys & 1 << 19
		draggStart = self.draggStart()
		isDragging = self.dragging()

		layer = self.editViewController().graphicView().activeLayer()
		node = find_selected_offcurve_node(layer)
		if not node:
			objc.super(HarmonicMove, self).moveSelectionWithPoint_withModifier_(delta, modidierKeys)
			return

		N, NN, P, PP = unpack_node(node)
		start = draggStart if isDragging else node.position
		target_position = addPoints(start, delta)


		x0, y0, x1, y1, x2, y2, x3, y3 = unpack_coords(node)
		initial_k = self.initial_dragging_k if isDragging else initial_curvature(node)

		if is_p1(node, N, P):
			if alt_pressed or P.smooth:
				target_position = projection(P, start, target_position)

			if x2 == x3:
				if x0 == target_position.x:
					NSBeep()
					return
				new_y2 = y2_from_k(x0, y0, target_position.x, target_position.y, x2, y2, x3, y3, initial_k)
				N.position = NSPoint(x2, new_y2)
			else:
				z, b = get_line_params(x2, y2, x3, y3)
				new_x2 = x_2_from_k(x0, y0, target_position.x, target_position.y, x2, y2, x3, y3, initial_k, z, b)

				N.position = NSPoint(new_x2, z * new_x2 + b)

		elif is_p2(node, N, P):
			if alt_pressed or N.smooth:
				target_position = projection(N, start, target_position)

			if x0 == x1:
				if target_position.x == x3:
					NSBeep()
					return
				new_y1 = y1_from_k(x0, y0, x1, y1, target_position.x, target_position.y, x3, y3, initial_k)
				P.position = NSPoint(x1, new_y1)

			else:
				z, b = get_line_params(x0, y0, x1, y1)
				new_x1 = x1_from_k(x0, y0, x1, y1, target_position.x, target_position.y, x3, y3, initial_k, z, b)
				P.position = NSPoint(new_x1, z * new_x1 + b)

		node.position = target_position


	def printInfo_(self, sender):
		if Glyphs.font.selectedLayers:
			layer = Glyphs.font.selectedLayers[0]
			print("Current layer:", layer.parent.name, layer.name)

	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
