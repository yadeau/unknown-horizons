# ###################################################
# Copyright (C) 2009 The Unknown Horizons Team
# team@unknown-horizons.org
# This file is part of Unknown Horizons.
#
# Unknown Horizons is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the
# Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# ###################################################

import horizons.main
import math
from horizons.util import Point, Rect

class BuildableSingle(object):
	"""Buildings you can build single.
	The Buildable* classes are a collection of classmethods checking the building
	requirements on a certain place, each returning None if build is not possible here.
	In case of a possible build location, a dict is returned with related attribute (possibly empty).
	TODO: document those return values
	"""
	@classmethod
	def are_build_requirements_satisfied(cls, x, y, before = None, **kwargs):
		state = {'x' : x, 'y' : y}
		state.update(kwargs)
		# apply all build checks
		for check in (cls.is_island_build_requirement_satisfied, \
									cls.is_settlement_build_requirement_satisfied, \
									cls.is_ground_build_requirement_satisfied, \
									cls.is_building_build_requirement_satisfied, \
									cls.is_unit_build_requirement_satisfied):
			update = check(**state)
			if update is None:
				return None
			else:
				state.update(update)
				if 'buildable' in update and update['buildable'] == False:
					return state
		if before is not None:
			update = cls.is_multi_build_requirement_satisfied(*before, **state)
			if update is None:
				return None
			else:
				state.update(update)
				if 'buildable' in update and update['buildable'] == False:
					return state
		return state

	@classmethod
	def is_multi_build_requirement_satisfied(cls, *before, **state):
		for i in before:
			if not i.get('buildable', True):
				continue
			if i['island'] != state['island']:
				return {'buildable' : False}
		return {}

	@classmethod
	def is_island_build_requirement_satisfied(cls, x, y, **state):
		island = horizons.main.session.world.get_island(Point(x, y))
		if island is None:
			return {'buildable' : False}
		p = Point(0, 0)
		for p.x, p.y in ((xx, yy) for xx in xrange(x, x + cls.size[0]) for yy in xrange(y, y + cls.size[1])):
			if island.get_tile(p) is None:
				return {'buildable' : False}
		return {'island' : island}

	@classmethod
	def is_settlement_build_requirement_satisfied(cls, x, y, island, **state):
		settlements = island.get_settlements(Rect(x, y, x + cls.size[0] - 1, y + cls.size[1] - 1))
		if len(settlements) != 1:
			return {'buildable' : False}
		return {'settlement' : settlements.pop()}

	@classmethod
	def is_ground_build_requirement_satisfied(cls, x, y, island, **state):
		p = Point(0, 0)
		for p.x, p.y in ((xx, yy) for xx in xrange(x, x + cls.size[0]) for yy in xrange(y, y + cls.size[1])):
			tile_classes = island.get_tile(p).__class__.classes
			if 'constructible' not in tile_classes:
				return {'buildable' : False}
		return {}

	@classmethod
	def is_building_build_requirement_satisfied(cls, x, y, island, **state):
		from nature import GrowingBuilding
		tear = []
		p = Point(0, 0)
		for p.x, p.y in ((xx, yy) for xx in xrange(x, x + cls.size[0]) for yy in xrange(y, y + cls.size[1])):
			obj = island.get_tile(p).object
			if obj is not None:
				if isinstance(obj, GrowingBuilding):
					if obj.__class__ is cls:
						return None
					tear.append(obj.getId())
				else:
					return {'buildable' : False}
		return {} if len(tear) == 0 else {'tear' : tear}

	@classmethod
	def is_unit_build_requirement_satisfied(cls, x, y, island, **state):
		return {}

	@classmethod
	def get_build_list(cls, point1, point2, **kwargs):
		# NOTE: point1 is unused here, why?
		x = int(round(point2[0])) - (cls.size[0] - 1) / 2 if \
			(cls.size[0] % 2) == 1 else int(math.ceil(point2[0])) - (cls.size[0]) / 2
		y = int(round(point2[1])) - (cls.size[1] - 1) / 2 if \
			(cls.size[1] % 2) == 1 else int(math.ceil(point2[1])) - (cls.size[1]) / 2
		building = cls.are_build_requirements_satisfied(x, y, **kwargs)
		if building is None:
			return []
		else:
			return [building]

class BuildableRect(BuildableSingle):
	@classmethod
	def get_build_list(cls, point1, point2, **kwargs):
		buildings = []
		for x, y in ((x, y) \
								 for x in xrange(int(min(round(point1[0]), round(point2[0]))), \
																 1 + int(max(round(point1[0]), round(point2[0])))) \
								 for y in xrange(int(min(round(point1[1]), round(point2[1]))), \
																 1 + int(max(round(point1[1]), round(point2[1]))))):
			building = cls.are_build_requirements_satisfied(x, y, buildings, **kwargs)
			if building is not None:
				buildings.append(building)

		return buildings

class BuildableLine(BuildableSingle):
	@classmethod
	def get_build_list(cls, point1, point2, **kwargs):
		"""
		@param point1:
		@param point2:
		"""
		buildings = []
		kwargs['rotation'] = 45
		point1_int = (int(round(point1[0])), int(round(point1[1])))
		point2_int = (int(round(point2[0])), int(round(point2[1])))
		y = point1_int[1]
		# iterate in x direction with fixed y
		for x in xrange(point1_int[0], point2_int[0], (1 if point2_int[0] > point1_int[0] else -1)):
			building = cls.are_build_requirements_satisfied(x, y, buildings, **kwargs)
			if building is not None:
				building.update({'action' : ('d' if point2_int[0] < point1_int[0] else 'b') if len(buildings) == 0 else 'bd'})
				buildings.append(building)
		x = point2_int[0]
		# iterate in y direction with fixed x
		for y in xrange(point1_int[1], \
										point2_int[1] + (1 if point2_int[1] > point1_int[1] else -1), \
										(1 if point2_int[1] > point1_int[1] else -1)):
			if len(buildings) == 0: #first tile
				if y == point2_int[1]: #only tile
					action = 'ac'
				else:
					action = 'c' if point2_int[1] > point1_int[1] else 'a'
			elif y == point2_int[1]: #last tile
				if point1_int[1] == point2_int[1]: #only tile in this loop
					action = 'd' if point2_int[0] > point1_int[0] else 'b'
				else:
					action = 'a' if point2_int[1] > point1_int[1] else 'c'
			elif y == point1_int[1]: #edge
				if point2_int[0] > point1_int[0]:
					action = 'cd' if point2_int[1] > point1_int[1] else 'ad'
				else:
					action = 'bc' if point2_int[1] > point1_int[1] else 'ab'
			else:
				action = 'ac' #default

			building = cls.are_build_requirements_satisfied(x, y, buildings, **kwargs)
			if building is not None:
				building.update({'action' : action})
				buildings.append(building)
		return buildings

class BuildableSingleWithSurrounding(BuildableSingle):
	@classmethod
	def get_build_list(cls, point1, point2, **kwargs):
		x = int(round(point2[0])) - (cls.size[0] - 1) / 2 if (cls.size[0] % 2) == 1 else int(math.ceil(point2[0])) - (cls.size[0]) / 2
		y = int(round(point2[1])) - (cls.size[1] - 1) / 2 if (cls.size[1] % 2) == 1 else int(math.ceil(point2[1])) - (cls.size[1]) / 2
		building = cls.are_build_requirements_satisfied(x, y, **kwargs)
		if building is None:
			return []
		buildings = [building]
		for xx in xrange(x - cls.radius, x + cls.size[0] + cls.radius):
			for yy in xrange(y - cls.radius, y + cls.size[1] + cls.radius):
				if ((xx < x or xx >= x + cls.size[0]) or (yy < y or yy >= y + cls.size[1])) and \
					 ((max(x - xx, 0, xx - x - cls.size[0] + 1) ** 2) + (max(y - yy, 0, yy - y - cls.size[1] + 1) ** 2)) <= cls.radius ** 2:
					building = horizons.main.session.entities.buildings[cls._surroundingBuildingClass].are_build_requirements_satisfied(xx, yy, **kwargs)
					if building is not None:
						building.update(building = horizons.main.session.entities.buildings[cls._surroundingBuildingClass], **kwargs)
						buildings.append(building)
		return buildings
