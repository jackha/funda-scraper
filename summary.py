# make a summary of some json file scraped from funda
import json
import argparse
import csv
import math


def distance(lat0, lon0, lat1, lon1):
	"""Rough guess of distance in km"""
	return math.sqrt((lat1 - lat0) ** 2 + (lon1 - lon0) ** 2) * 111

class Layout:
	default = "\033[0m"
	bold = "\033[1m"
	dim = "\033[2m"
	red = "\033[31m"
	green = "\033[32m"


class House(object):
	def __init__(self, obj, location, pois):
		self._orig = obj  # the base dict

		self._extra = {
			"price_per_m2": float(obj["price"]) / float(obj["area"]),
			"location": location,
			"distance_to_poi": ", ".join(["%s:%0.2fkm" % (poi["name"], distance(poi["lat"], poi["lon"], location["lat"], location["lon"])) for poi in pois]),
			"district": location["district"],
			"magic": -int(obj["area"])*3 + float(obj["price"]) / 1000 
			}

		for i, poi in enumerate(pois):
			self._extra["distance%i" % i] = distance(poi["lat"], poi["lon"], location["lat"], location["lon"])

	def get_property(self, property):
		if property in self._orig:
			return self._orig[property]
		if property in self._extra:
			return self._extra[property]
		return None

	def __str__(self):
		result = "%s, %s, %s, price(%s), area(%s), price per m2(%0.0f), year(%s), type(%s), rooms(%s), bedrooms(%s)" % (
			self._orig["address"], self._extra["district"], self._orig["postal_code"], self._orig["price"], self._orig["area"], self._extra["price_per_m2"], 
			self._orig["year_built"], self._orig["property_type"], self._orig["rooms"], self._orig["bedrooms"])
		if int(self._orig["price"]) >= 375000:
			result = Layout.dim + Layout.red + result + Layout.default
		if int(self._orig["price"]) <= 300000:
			result = Layout.green + result + Layout.default
		return result


class HouseCollection(object):
	def __init__(self):
		self.houses = set()

	def add(self, house):
		self.houses.add(house)

	def print_summary(self):
		min_price = None
		max_price = None
		best_price_per_m2 = None
		min_price_house = None
		max_price_house = None
		best_price_per_m2_house = None
		for house in self.houses:
			price = house.get_property("price")
			price_per_m2 = house.get_property("price_per_m2")
			if min_price is None or price < min_price:
				min_price = price
				min_price_house = house
			if max_price is None or price > max_price:
				max_price = price
				max_price_house = house
			if best_price_per_m2 is None or price_per_m2 < best_price_per_m2:
				best_price_per_m2 = price_per_m2
				best_price_per_m2_house = house

		print("Aaaand the winners are:")
		print("Min price: [%s]: %s" % (min_price, str(min_price_house)))
		print("Max price: [%s]: %s" % (max_price, str(max_price_house)))
		print("Best price per m2: [%s]: %s" % (best_price_per_m2, str(best_price_per_m2_house)))

	def filter(self, *args, **kwargs):
		result = HouseCollection()
		for k, v in kwargs.items():
			for house in self.houses:
				if house.get_property(k) == v:
					result.add(house)
		return result

	def sort_by(self, criteria):
		return sorted(self.houses, key=lambda h: h.get_property(criteria))


class PostalCodes(object):
	PATCHES = [
		(3531, 52.091177, 5.098962),  # Lombok
		(3532, 52.095363, 5.089510),  # majellapark
	]
	PATCH_DISTRICT = [
		(3554, "Zuilen2"),  
		(3553, "Zuilen3"), 
		(3544, "Leidsche Rijn2"),
		(3563, "Overvecht-Noord2"),
	]

	def __init__(self, data):
		"""
		Postal Code,Place Name,State,County,Latitude,Longitude
		9400,Assen,Provincie Drenthe,Gemeente Assen,52.9967,6.5625
		"""
		self.lookup = {}
		with open("nl_postal_codes.csv", "r", encoding="mac_roman") as f:
			reader = csv.reader(f, delimiter=',')
			for line in reader:
				if "Postal Code" in line:
					continue
				a,b,c,d,e,f = line
				self.lookup[a] = {"district": b, "province": c, "municipality": d, "lat": float(e), "lon": float(f)}

		# some patches:
		for pc,lat,lon in self.PATCHES:
			self.lookup[str(pc)]["lat"] = lat
			self.lookup[str(pc)]["lon"] = lon

		for pc,district in self.PATCH_DISTRICT:
			self.lookup[str(pc)]["district"] = district

	def get(self, postal_code):
		return self.lookup[postal_code]


POI = [
	{"name": "centrum (bijenkorf)", "lat": 52.093202, "lon": 5.114780}, 
	{"name": "wouthor", "lat": 52.110566, "lon": 5.090744},
	{"name": "station", "lat": 52.089617, "lon": 5.110537},
	{"name": "centrum (ledig erf)", "lat": 52.081741, "lon": 5.123774},
	]

# DISTRICTS = [
# 	"Zuilen", "Oog in Al", "Hoograven", "Hogeweide", "Leidsche Rijn", "Tuindorp", "Lunetten", 
# 	"Rivierenwijk", "Oudwijk", "Dichterswijk", "Kanaleneiland", 
# 	"Wittevrouwen", "Tolsteeg/Hoograven", "Overvecht-Noord", "Overvecht-Zuid", 
# 	"Ondiep", "Lombok", "Majellapark", "Binnenstad", "2e Daalsebuurt, Bomenbuurt, Amsterdamsestraatweg na spoorviaduct",  
# 	"Voordorp", "Schepenbuurt, industrieterrein Cartesiusweg",
#   "Zuilen2", "Zuilen3", "Leidsche Rijn2", "Overvecht-Noord2"
# 	]

DISTRICTS = [
	"Zuilen", "Zuilen2", "Zuilen3", "Ondiep", "Hogeweide", # "Leidsche Rijn", 
	]

if __name__ == "__main__": 
	parser = argparse.ArgumentParser(description="")
	parser.add_argument("filename", type=str, help="filename")

	args = parser.parse_args()

	with open(args.filename) as f:
		data = json.load(f)

	postal_codes = PostalCodes("nl_postal_codes.csv")

	# data is a list with dicts
	# dict looks like: {"city": "Utrecht", "year_built": "1992", "area": "80", "url": "http://www.funda.nl/koop/utrecht/appartement-49963140-arthur-van-schendelstraat-35/", "price": "300000", "bedrooms": "2", "postal_code": "3511 MA", "rooms": "3", "address": "Arthur van Schendelstraat 35", "property_type": "apartment"}

	house_collection = HouseCollection()
	used_postal_codes = {}  # see which ones are used
	for obj in data:
		# some rejection criteria
		if int(obj["price"]) < 10000:
			# software mistake
			continue
		if int(obj["price"]) > 600000:
			# too expensive
			continue
		if obj["property_type"] != "house":
			continue
		if int(obj["area"]) < 110:
			continue

		# 9400,Assen,Provincie Drenthe,Gemeente Assen,52.9967,6.5625
		location = postal_codes.get(obj["postal_code"][:4])
		used_postal_codes[obj["postal_code"][:4]] = location
		house_collection.add(House(obj, location, POI))

	print(Layout.default)
	print("#"*160)
	# house_collection.print_summary()
	for district in DISTRICTS:
		# house_list = house_collection.filter(district=district).sort_by("price_per_m2")
		house_list = house_collection.filter(district=district).sort_by("magic")
		# house_list = house_collection.filter(district=district).sort_by("area")
		# house_list = house_collection.sort_by("distance0")
		# house_list.reverse()

		print("District [%s]" % district)
		for i, house in enumerate(house_list[:20]):
			print("%2d %s" % (i, str(house)))
			print("   %s%s%s" % (Layout.dim, house.get_property("url"), Layout.default))
		print()

	# print(", ".join(["\"%s\"" % v["district"] for v in used_postal_codes.values()]))
	#for k, v in used_postal_codes.items():
	#	print("%s %s" % (k, v["district"]))