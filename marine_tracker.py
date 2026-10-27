import os
import re
import math
import time
import heapq
import functools
import threading
import logging
import requests
import datetime
from flask import Flask, render_template, request
from flask_socketio import SocketIO

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "MarineTrackerFinland/1.0", "Digitraffic-User": "MarineTrackerFinland/1.0"}
MARINE_LOC_URL = "https://meri.digitraffic.fi/api/ais/v1/locations"
MARINE_META_URL = "https://meri.digitraffic.fi/api/ais/v1/vessels"
MARINE_PORTS_URL = "https://meri.digitraffic.fi/api/port-call/v1/ports"
MARINE_WINTER_PORTS_URL = "https://meri.digitraffic.fi/api/winter-navigation/v2/locations"
MARINE_PORT_CALLS_URL = "https://meri.digitraffic.fi/api/port-call/v1/port-calls"

FETCH_INTERVAL = 15

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

vessels_metadata = {}
port_calls_by_mmsi = {}
ports_by_code = {}
ports_by_name = {}
vessel_trails = {}   # mmsi -> list of [lat, lon]
vessel_origins = {}  # mmsi -> cached inferred origin dict
latest_data_cache = []
history_data = {"times": [], "counts": []}
latest_stats_cache = {}

# Curated fallback coordinates for major Baltic, Finnish, and international ports
CUSTOM_PORTS = {
    "FIHEL": {"code": "FIHEL", "name": "Helsinki", "lat": 60.155, "lon": 24.955},
    "FIVSS": {"code": "FIVSS", "name": "Vuosaari (Helsinki)", "lat": 60.215, "lon": 25.190},
    "FIHKO": {"code": "FIHKO", "name": "Hanko", "lat": 59.820, "lon": 22.970},
    "FITKU": {"code": "FITKU", "name": "Turku", "lat": 60.435, "lon": 22.220},
    "FINLI": {"code": "FINLI", "name": "Naantali", "lat": 60.468, "lon": 22.026},
    "FIMHQ": {"code": "FIMHQ", "name": "Mariehamn", "lat": 60.093, "lon": 19.928},
    "FILAN": {"code": "FILAN", "name": "Långnäs", "lat": 60.116, "lon": 20.298},
    "FIECK": {"code": "FIECK", "name": "Eckerö", "lat": 60.223, "lon": 19.538},
    "FIKTK": {"code": "FIKTK", "name": "Kotka", "lat": 60.460, "lon": 26.945},
    "FIHMN": {"code": "FIHMN", "name": "Hamina", "lat": 60.535, "lon": 27.185},
    "FIINK": {"code": "FIINK", "name": "Inkoo", "lat": 60.020, "lon": 23.920},
    "FIVKO": {"code": "FIVKO", "name": "Valko (Loviisa)", "lat": 60.412, "lon": 26.258},
    "FIRAU": {"code": "FIRAU", "name": "Rauma", "lat": 61.127, "lon": 21.452},
    "FIPOR": {"code": "FIPOR", "name": "Pori", "lat": 61.590, "lon": 21.488},
    "FIVAA": {"code": "FIVAA", "name": "Vaasa", "lat": 63.088, "lon": 21.560},
    "FIKOK": {"code": "FIKOK", "name": "Kokkola", "lat": 63.842, "lon": 23.025},
    "FIPRS": {"code": "FIPRS", "name": "Pietarsaari", "lat": 63.708, "lon": 22.688},
    "FIRAA": {"code": "FIRAA", "name": "Raahe", "lat": 64.665, "lon": 24.405},
    "FIOUL": {"code": "FIOUL", "name": "Oulu", "lat": 65.000, "lon": 25.415},
    "FIKEM": {"code": "FIKEM", "name": "Kemi", "lat": 65.670, "lon": 24.515},
    "FITOR": {"code": "FITOR", "name": "Tornio", "lat": 65.748, "lon": 24.168},
    "FIKAS": {"code": "FIKAS", "name": "Kaskinen", "lat": 62.382, "lon": 21.218},
    "FIUKI": {"code": "FIUKI", "name": "Uusikaupunki", "lat": 60.795, "lon": 21.385},
    "FIPAR": {"code": "FIPAR", "name": "Parainen", "lat": 60.285, "lon": 22.290},
    "FIFOR": {"code": "FIFOR", "name": "Förby", "lat": 60.090, "lon": 22.868},
    "FISKV": {"code": "FISKV", "name": "Sköldvik (Porvoo)", "lat": 60.304, "lon": 25.546},
    "FIKRS": {"code": "FIKRS", "name": "Kristiinankaupunki", "lat": 62.268, "lon": 21.365},
    "FISAL": {"code": "FISAL", "name": "Salo", "lat": 60.355, "lon": 23.100},
    "FITEI": {"code": "FITEI", "name": "Teijo", "lat": 60.254, "lon": 22.946},
    "FIKUS": {"code": "FIKUS", "name": "Kustavi", "lat": 60.536, "lon": 21.352},
    "EETLL": {"code": "EETLL", "name": "Tallinn", "lat": 59.448, "lon": 24.765},
    "EEVAN": {"code": "EEVAN", "name": "Tallinn (Vanasadam)", "lat": 59.445, "lon": 24.768},
    "EEMUG": {"code": "EEMUG", "name": "Muuga", "lat": 59.492, "lon": 24.958},
    "EEPLS": {"code": "EEPLS", "name": "Paldiski", "lat": 59.350, "lon": 24.048},
    "EESLM": {"code": "EESLM", "name": "Sillamäe", "lat": 59.412, "lon": 27.738},
    "EERMS": {"code": "EERMS", "name": "Roomassaare", "lat": 58.213, "lon": 22.507},
    "EEPRN": {"code": "EEPRN", "name": "Pärnu", "lat": 58.382, "lon": 24.475},
    "SESTO": {"code": "SESTO", "name": "Stockholm", "lat": 59.335, "lon": 18.110},
    "SEKAP": {"code": "SEKAP", "name": "Kapellskär", "lat": 59.718, "lon": 19.067},
    "SEKPS": {"code": "SEKPS", "name": "Kapellskär", "lat": 59.718, "lon": 19.067},
    "SEGRH": {"code": "SEGRH", "name": "Grisslehamn", "lat": 60.098, "lon": 18.814},
    "SEGOT": {"code": "SEGOT", "name": "Göteborg", "lat": 57.695, "lon": 11.895},
    "SEPIT": {"code": "SEPIT", "name": "Piteå", "lat": 65.235, "lon": 21.568},
    "SENOT": {"code": "SENOT", "name": "Norrsundet", "lat": 60.930, "lon": 17.155},
    "SESSR": {"code": "SESSR", "name": "Sandarne", "lat": 61.263, "lon": 17.175},
    "SEGVX": {"code": "SEGVX", "name": "Gävle", "lat": 60.690, "lon": 17.220},
    "SELUL": {"code": "SELUL", "name": "Luleå", "lat": 65.555, "lon": 22.250},
    "SEUME": {"code": "SEUME", "name": "Umeå", "lat": 63.692, "lon": 20.340},
    "SESDL": {"code": "SESDL", "name": "Sundsvall", "lat": 62.390, "lon": 17.345},
    "SENYN": {"code": "SENYN", "name": "Nynäshamn", "lat": 58.905, "lon": 17.955},
    "SEOXE": {"code": "SEOXE", "name": "Oxelösund", "lat": 58.665, "lon": 17.110},
    "SENRK": {"code": "SENRK", "name": "Norrköping", "lat": 58.610, "lon": 16.225},
    "RUULU": {"code": "RUULU", "name": "Ust-Luga", "lat": 59.685, "lon": 28.402},
    "RULED": {"code": "RULED", "name": "St. Petersburg", "lat": 59.915, "lon": 30.220},
    "RUPRI": {"code": "RUPRI", "name": "Primorsk", "lat": 60.340, "lon": 28.705},
    "RUVYS": {"code": "RUVYS", "name": "Vysotsk", "lat": 60.620, "lon": 28.570},
    "RUKGD": {"code": "RUKGD", "name": "Kaliningrad", "lat": 54.695, "lon": 20.450},
    "RUKLD": {"code": "RUKLD", "name": "Kaliningrad", "lat": 54.695, "lon": 20.450},
    "RUMMK": {"code": "RUMMK", "name": "Murmansk", "lat": 68.975, "lon": 33.055},
    "DETRV": {"code": "DETRV", "name": "Travemünde", "lat": 53.958, "lon": 10.872},
    "DERSK": {"code": "DERSK", "name": "Rostock", "lat": 54.150, "lon": 12.100},
    "DEKEL": {"code": "DEKEL", "name": "Kiel", "lat": 54.330, "lon": 10.155},
    "DELBC": {"code": "DELBC", "name": "Lübeck", "lat": 53.885, "lon": 10.700},
    "DEBRB": {"code": "DEBRB", "name": "Brunsbüttel", "lat": 53.888, "lon": 9.142},
    "DEWVN": {"code": "DEWVN", "name": "Wilhelmshaven", "lat": 53.518, "lon": 8.148},
    "DEHAM": {"code": "DEHAM", "name": "Hamburg", "lat": 53.540, "lon": 9.970},
    "DEBRV": {"code": "DEBRV", "name": "Bremerhaven", "lat": 53.550, "lon": 8.560},
    "PLGDY": {"code": "PLGDY", "name": "Gdynia", "lat": 54.533, "lon": 18.550},
    "PLGDN": {"code": "PLGDN", "name": "Gdańsk", "lat": 54.405, "lon": 18.670},
    "PLSWI": {"code": "PLSWI", "name": "Świnoujście", "lat": 53.910, "lon": 14.260},
    "PLSZZ": {"code": "PLSZZ", "name": "Szczecin", "lat": 53.430, "lon": 14.580},
    "LVRIX": {"code": "LVRIX", "name": "Riga", "lat": 57.035, "lon": 24.045},
    "LVVNT": {"code": "LVVNT", "name": "Ventspils", "lat": 57.400, "lon": 21.545},
    "LVLPX": {"code": "LVLPX", "name": "Liepāja", "lat": 56.525, "lon": 20.995},
    "LTKLJ": {"code": "LTKLJ", "name": "Klaipėda", "lat": 55.705, "lon": 21.120},
    "NLRTM": {"code": "NLRTM", "name": "Rotterdam", "lat": 51.950, "lon": 4.140},
    "NLAMS": {"code": "NLAMS", "name": "Amsterdam", "lat": 52.410, "lon": 4.800},
    "NLVLI": {"code": "NLVLI", "name": "Vlissingen", "lat": 51.445, "lon": 3.595},
    "NLMOE": {"code": "NLMOE", "name": "Moerdijk", "lat": 51.690, "lon": 4.580},
    "BEANR": {"code": "BEANR", "name": "Antwerp", "lat": 51.260, "lon": 4.350},
    "BEZEE": {"code": "BEZEE", "name": "Zeebrugge", "lat": 51.335, "lon": 3.205},
    "TRISK": {"code": "TRISK", "name": "Iskenderun", "lat": 36.592, "lon": 36.175},
    "TRALI": {"code": "TRALI", "name": "Aliağa", "lat": 38.805, "lon": 26.945},
    "EGPSD": {"code": "EGPSD", "name": "Port Said", "lat": 31.265, "lon": 32.305},
    "EGSUZ": {"code": "EGSUZ", "name": "Suez", "lat": 29.955, "lon": 32.555},
    "ELDAB": {"code": "ELDAB", "name": "El Dabaa", "lat": 31.045, "lon": 28.440},
    "GIGIB": {"code": "GIGIB", "name": "Gibraltar", "lat": 36.140, "lon": -5.365},
    "NOGLO": {"code": "NOGLO", "name": "Glomfjord", "lat": 66.818, "lon": 13.942},
    "NOMON": {"code": "NOMON", "name": "Mongstad", "lat": 60.812, "lon": 5.032},
    "PACTB": {"code": "PACTB", "name": "Cristóbal", "lat": 9.350, "lon": -79.905},
}

NAME_ALIASES = {
    "UST LUGA": "RUULU", "UST-LUGA": "RUULU", "USTLUGA": "RUULU", "UST'-LUGA": "RUULU",
    "RU UST-LUGA": "RUULU", "RU_ULU": "RUULU", "UST-LUGA RUSSIA": "RUULU",
    "ST.PETERBURG": "RULED", "ST.PETERSBURG": "RULED", "SAINT-PETERSBURG": "RULED",
    "ST.BURG": "RULED", "SPB": "RULED", "PRIMORSK": "RUPRI", "VYSOTSK": "RUVYS",
    "KALININGRAD": "RUKGD", "EL DABAA": "ELDAB", "PORT SAID": "EGPSD",
    "WILHELMSHAVEN": "DEWVN", "TRAVEMUNDE": "DETRV", "TRAVEMUENDE": "DETRV",
    "GDYNIA": "PLGDY", "GDANSK": "PLGDN", "GOTEBORG": "SEGOT", "GOTHENBURG": "SEGOT",
    "STOCKHOLM": "SESTO", "KAPELLSKAR": "SEKAP", "GRISSLEHAMN": "SEGRH",
    "TALLINN": "EETLL", "MUUGA": "EEMUG", "PALDISKI": "EEPLS", "SILLAMAE": "EESLM",
    "HELSINKI": "FIHEL", "VUOSAARI": "FIVSS", "HANKO": "FIHKO", "HANGO": "FIHKO",
    "TURKU": "FITKU", "ABO": "FITKU", "NAANTALI": "FINLI", "MARIEHAMN": "FIMHQ",
    "LANGNAS": "FILAN", "ECKERO": "FIECK", "KOTKA": "FIKTK", "HAMINA": "FIHMN",
    "RAUMA": "FIRAU", "PORI": "FIPOR", "VAASA": "FIVAA", "KOKKOLA": "FIKOK",
    "PIETARSAARI": "FIPRS", "JAKOBSTAD": "FIPRS", "RAAHE": "FIRAA", "OULU": "FIOUL",
    "KEMI": "FIKEM", "TORNIO": "FITOR", "INKOO": "FIINK", "INGA": "FIINK",
    "LOVIISA": "FIVKO", "VALKO": "FIVKO", "VALKOM": "FIVKO", "PORVOO": "FISKV",
    "SKOLDVIK": "FISKV", "UUSIKAUPUNKI": "FIUKI", "KASKINEN": "FIKAS",
    "PARAINEN": "FIPAR", "FORBY": "FIFOR",
}

BALTIC_HUB_CODES = [
    "FIHEL", "FIVSS", "FIHKO", "FITKU", "FINLI", "FIMHQ", "FILAN", "FIECK",
    "FIKTK", "FIHMN", "FIINK", "FIVKO", "FIRAU", "FIPOR", "FIVAA", "FIKOK",
    "FIPRS", "FIRAA", "FIOUL", "FIKEM", "FITOR", "FIKAS", "FIUKI", "FISKV",
    "EETLL", "EEMUG", "EEPLS", "EESLM", "EERMS", "SESTO", "SEKAP", "SEGRH",
    "SEGVX", "SELUL", "SEUME", "SESDL", "SENYN", "SEOXE", "RUULU", "RULED",
    "RUPRI", "RUVYS", "RUKGD", "DETRV", "DERSK", "DEKEL", "PLGDY", "PLGDN",
    "LVRIX", "LVVNT", "LTKLJ"
]

# Maritime Fairway & Sea-Lane Graph (137 real sea waypoints across Gulf of Finland, Archipelago, Bothnia, Baltic & Europe)
SEA_NODES = {
    "W_SPB_CH": (59.950, 29.850), "W_KRON": (60.000, 29.450), "W_USTLUGA_N": (59.820, 28.350),
    "W_SESKAR": (60.030, 28.250), "W_VYSOTSK_S": (60.480, 28.480), "W_PRIMORSK_S": (60.260, 28.620),
    "W_SOMMERS": (60.160, 27.600), "W_HAMINA_S": (60.360, 27.180), "W_KOTKA_S": (60.320, 26.940),
    "W_HOGLAND_N": (60.150, 26.950), "W_HOGLAND_S": (59.850, 26.900), "W_SILLAMAE_N": (59.560, 27.720),
    "W_ORRENGRUND": (60.120, 26.420), "W_LOVIISA_S": (60.240, 26.260), "W_KALBADA": (59.950, 25.600),
    "W_SKOLDVIK_S": (60.160, 25.550), "W_VUOSAARI_S": (60.080, 25.220), "W_HARMAJA": (60.085, 24.970),
    "W_HEL_LIGHT": (59.945, 24.925), "W_MUUGA_N": (59.580, 25.000), "W_TALLINN_N": (59.620, 24.760),
    "W_TALLINN_BAY": (59.500, 24.750), "W_PORKKALA": (59.840, 24.450), "W_NAISSAAR": (59.650, 24.400),
    "W_INKOO_S": (59.880, 23.950), "W_PALDISKI_N": (59.480, 23.950), "W_JUSSARO": (59.730, 23.580),
    "W_OSMUSAAR": (59.420, 23.300), "W_RUSSARO": (59.720, 22.960), "W_HANKO_W": (59.780, 22.750),
    "W_BENGTSKAR": (59.650, 22.480), "W_HIIUMAA_N": (59.250, 22.400), "W_HIIUMAA_W": (58.950, 21.800),
    "W_FORBY_W": (60.030, 22.720), "W_SALO_S": (60.180, 22.880), "W_PARAINEN_S": (60.160, 22.250),
    "W_AIRISTO": (60.260, 22.120), "W_NAANTALI_S": (60.410, 22.050), "W_KORPO": (60.140, 21.600),
    "W_UTO": (59.740, 21.350), "W_KOKAR": (59.920, 20.950), "W_SOTTUNGA": (60.080, 20.650),
    "W_LANGNAS_E": (60.115, 20.350), "W_LEDSUND": (59.950, 20.150), "W_MARIEHAMN_S": (59.980, 19.930),
    "W_NYHAMN": (59.920, 19.850), "W_FLOTJAN": (59.800, 19.750), "W_SODERARM": (59.750, 19.420),
    "W_KAPELL_E": (59.720, 19.180), "W_FURUSUND": (59.640, 18.950), "W_SANDHAMN": (59.420, 19.050),
    "W_VAXHOLM": (59.380, 18.380), "W_ALAND_S": (59.950, 19.250), "W_GRISSLE_E": (60.100, 18.980),
    "W_ECKERO_W": (60.220, 19.380), "W_MARKET": (60.280, 19.150), "W_KUSTAVI_W": (60.550, 21.100),
    "W_BOTH_SW": (60.650, 18.800), "W_BOTH_SE": (60.650, 20.500), "W_UKI_W": (60.800, 20.950),
    "W_RAUMA_W": (61.130, 21.100), "W_PORI_W": (61.600, 21.100), "W_GAVLE_E": (60.720, 17.650),
    "W_NORRSUND_E": (60.950, 17.550), "W_SANDARNE_E": (61.260, 17.650), "W_SUNDSVALL_E": (62.350, 17.950),
    "W_BOTH_MW": (61.800, 18.800), "W_BOTH_ME": (61.950, 20.750), "W_KRISTIINA_W": (62.220, 21.050),
    "W_KASKINEN_W": (62.350, 20.900), "W_KVARKEN_S": (62.850, 20.500), "W_KVARKEN_M": (63.150, 20.700),
    "W_VAASA_W": (63.120, 21.150), "W_KVARKEN_N": (63.500, 21.100), "W_UMEA_E": (63.580, 20.550),
    "W_BAY_S": (63.800, 21.950), "W_PIETAR_W": (63.760, 22.350), "W_KOKKOLA_W": (63.920, 22.650),
    "W_RAAHE_W": (64.650, 23.850), "W_OULU_W": (65.080, 24.350), "W_OULU_CH": (65.040, 25.100),
    "W_KEMI_S": (65.450, 24.400), "W_LULEA_E": (65.350, 22.650), "W_PITEA_E": (65.100, 21.950),
    "W_BOGSKAR": (59.450, 20.400), "W_BALT_NC": (59.100, 20.600), "W_GOTSKA": (58.550, 19.550),
    "W_LANDSORT": (58.650, 18.150), "W_OXELO_E": (58.600, 17.450), "W_GOTLAND_E": (57.500, 19.450),
    "W_GOTLAND_W": (57.600, 17.500), "W_IRBE": (57.750, 21.700), "W_ROOMA_S": (58.050, 22.450),
    "W_RIGA_GULF": (57.350, 23.550), "W_PARNU_W": (58.150, 24.150), "W_VENTSPILS_W": (57.400, 21.100),
    "W_LIEPAJA_W": (56.520, 20.550), "W_KLAIPEDA_W": (55.720, 20.600), "W_KALIN_W": (54.700, 19.850),
    "W_GDANSK_N": (54.800, 18.850), "W_HOBURGEN": (56.750, 18.450), "W_OLAND_S": (56.000, 16.750),
    "W_BORNHOLM_N": (55.450, 14.650), "W_BORNHOLM_S": (54.800, 15.200), "W_SWINO_N": (54.150, 14.280),
    "W_ARKONA": (54.750, 13.700), "W_DARSS": (54.550, 12.400), "W_ROSTOCK_N": (54.300, 12.080),
    "W_FEHMARN": (54.520, 11.350), "W_LUBECK_BAY": (54.120, 11.000), "W_KIEL_BIGHT": (54.450, 10.300),
    "W_KIEL_WEST": (53.890, 9.150), "W_ELBE_OUT": (53.980, 8.300), "W_FALSTERBO": (55.320, 12.750),
    "W_SOUND": (55.850, 12.650), "W_KATTEGAT": (56.850, 11.650), "W_GOTEBORG_W": (57.650, 11.450),
    "W_SKAGEN": (57.850, 10.600), "W_SKAGERRAK": (57.800, 8.000), "W_HELGOLAND": (54.250, 7.500),
    "W_TEXEL": (53.200, 4.300), "W_EUROPOORT": (52.000, 3.800), "W_SCHELDT": (51.420, 3.400),
    "W_DOVER": (51.050, 1.500), "W_USHANT": (48.500, -5.500), "W_FINISTERRE": (43.200, -9.800),
    "W_ST_VINCENT": (36.800, -9.200), "W_GIBRALTAR": (35.980, -5.500), "W_MED_W": (37.200, 3.000),
    "W_SICILY": (37.300, 11.500), "W_CRETE_S": (34.500, 24.500), "W_AEGEAN": (36.500, 25.800),
    "W_MED_E": (33.500, 30.500), "W_NORWAY_SW": (59.000, 4.800), "W_NORWAY_MID": (63.500, 6.500),
    "W_LOFOTEN": (68.000, 11.500), "W_NORTHCAPE": (71.300, 25.500),
}

SEA_EDGES = [
    ("W_SPB_CH", "W_KRON"), ("W_KRON", "W_SESKAR"), ("W_KRON", "W_PRIMORSK_S"),
    ("W_PRIMORSK_S", "W_VYSOTSK_S"), ("W_PRIMORSK_S", "W_SESKAR"), ("W_VYSOTSK_S", "W_SOMMERS"),
    ("W_USTLUGA_N", "W_SESKAR"), ("W_USTLUGA_N", "W_SILLAMAE_N"), ("W_USTLUGA_N", "W_HOGLAND_S"),
    ("W_SESKAR", "W_SOMMERS"), ("W_SESKAR", "W_HOGLAND_S"), ("W_SILLAMAE_N", "W_HOGLAND_S"),
    ("W_SOMMERS", "W_HAMINA_S"), ("W_SOMMERS", "W_HOGLAND_N"), ("W_HAMINA_S", "W_KOTKA_S"),
    ("W_HAMINA_S", "W_HOGLAND_N"), ("W_KOTKA_S", "W_HOGLAND_N"), ("W_KOTKA_S", "W_ORRENGRUND"),
    ("W_HOGLAND_N", "W_ORRENGRUND"), ("W_HOGLAND_N", "W_HOGLAND_S"), ("W_HOGLAND_S", "W_KALBADA"),
    ("W_HOGLAND_S", "W_MUUGA_N"), ("W_ORRENGRUND", "W_LOVIISA_S"), ("W_ORRENGRUND", "W_KALBADA"),
    ("W_LOVIISA_S", "W_KALBADA"), ("W_KALBADA", "W_SKOLDVIK_S"), ("W_KALBADA", "W_VUOSAARI_S"),
    ("W_KALBADA", "W_HEL_LIGHT"), ("W_KALBADA", "W_MUUGA_N"), ("W_SKOLDVIK_S", "W_VUOSAARI_S"),
    ("W_VUOSAARI_S", "W_HARMAJA"), ("W_VUOSAARI_S", "W_HEL_LIGHT"), ("W_HARMAJA", "W_HEL_LIGHT"),
    ("W_HEL_LIGHT", "W_MUUGA_N"), ("W_HEL_LIGHT", "W_TALLINN_N"), ("W_HEL_LIGHT", "W_PORKKALA"),
    ("W_MUUGA_N", "W_TALLINN_N"), ("W_TALLINN_N", "W_TALLINN_BAY"), ("W_TALLINN_N", "W_NAISSAAR"),
    ("W_TALLINN_N", "W_PORKKALA"), ("W_TALLINN_BAY", "W_NAISSAAR"), ("W_PORKKALA", "W_NAISSAAR"),
    ("W_PORKKALA", "W_INKOO_S"), ("W_PORKKALA", "W_JUSSARO"), ("W_NAISSAAR", "W_PALDISKI_N"),
    ("W_INKOO_S", "W_JUSSARO"), ("W_PALDISKI_N", "W_JUSSARO"), ("W_PALDISKI_N", "W_OSMUSAAR"),
    ("W_JUSSARO", "W_OSMUSAAR"), ("W_JUSSARO", "W_RUSSARO"), ("W_OSMUSAAR", "W_RUSSARO"),
    ("W_OSMUSAAR", "W_BENGTSKAR"), ("W_OSMUSAAR", "W_HIIUMAA_N"), ("W_RUSSARO", "W_HANKO_W"),
    ("W_RUSSARO", "W_BENGTSKAR"), ("W_HANKO_W", "W_BENGTSKAR"), ("W_HANKO_W", "W_FORBY_W"),
    ("W_BENGTSKAR", "W_UTO"), ("W_BENGTSKAR", "W_HIIUMAA_N"), ("W_BENGTSKAR", "W_BOGSKAR"),
    ("W_HIIUMAA_N", "W_HIIUMAA_W"), ("W_HIIUMAA_N", "W_UTO"), ("W_HIIUMAA_N", "W_BOGSKAR"),
    ("W_HIIUMAA_W", "W_BALT_NC"), ("W_HIIUMAA_W", "W_IRBE"),
    ("W_FORBY_W", "W_SALO_S"), ("W_FORBY_W", "W_PARAINEN_S"), ("W_FORBY_W", "W_BENGTSKAR"),
    ("W_PARAINEN_S", "W_AIRISTO"), ("W_AIRISTO", "W_NAANTALI_S"), ("W_AIRISTO", "W_KORPO"),
    ("W_AIRISTO", "W_UTO"), ("W_KORPO", "W_UTO"), ("W_KORPO", "W_KOKAR"), ("W_KORPO", "W_SOTTUNGA"),
    ("W_KORPO", "W_KUSTAVI_W"), ("W_UTO", "W_KOKAR"), ("W_UTO", "W_BOGSKAR"), ("W_KOKAR", "W_SOTTUNGA"),
    ("W_KOKAR", "W_LEDSUND"), ("W_KOKAR", "W_BOGSKAR"), ("W_SOTTUNGA", "W_LANGNAS_E"),
    ("W_SOTTUNGA", "W_BOTH_SE"), ("W_LANGNAS_E", "W_LEDSUND"), ("W_LEDSUND", "W_MARIEHAMN_S"),
    ("W_LEDSUND", "W_NYHAMN"), ("W_LEDSUND", "W_FLOTJAN"), ("W_MARIEHAMN_S", "W_NYHAMN"),
    ("W_NYHAMN", "W_FLOTJAN"), ("W_NYHAMN", "W_ALAND_S"), ("W_FLOTJAN", "W_SODERARM"),
    ("W_FLOTJAN", "W_ALAND_S"), ("W_FLOTJAN", "W_BOGSKAR"), ("W_SODERARM", "W_KAPELL_E"),
    ("W_SODERARM", "W_FURUSUND"), ("W_SODERARM", "W_SANDHAMN"), ("W_SODERARM", "W_ALAND_S"),
    ("W_KAPELL_E", "W_FURUSUND"), ("W_FURUSUND", "W_VAXHOLM"), ("W_SANDHAMN", "W_VAXHOLM"),
    ("W_SANDHAMN", "W_LANDSORT"), ("W_SANDHAMN", "W_BOGSKAR"), ("W_ALAND_S", "W_GRISSLE_E"),
    ("W_ALAND_S", "W_MARKET"), ("W_ALAND_S", "W_ECKERO_W"), ("W_GRISSLE_E", "W_ECKERO_W"),
    ("W_GRISSLE_E", "W_MARKET"), ("W_ECKERO_W", "W_MARKET"), ("W_MARKET", "W_BOTH_SW"),
    ("W_MARKET", "W_BOTH_SE"), ("W_KUSTAVI_W", "W_BOTH_SE"), ("W_KUSTAVI_W", "W_UKI_W"),
    ("W_BOTH_SW", "W_BOTH_SE"), ("W_BOTH_SW", "W_GAVLE_E"), ("W_BOTH_SW", "W_NORRSUND_E"),
    ("W_BOTH_SW", "W_BOTH_MW"), ("W_BOTH_SE", "W_UKI_W"), ("W_BOTH_SE", "W_RAUMA_W"),
    ("W_BOTH_SE", "W_BOTH_MW"), ("W_BOTH_SE", "W_BOTH_ME"), ("W_UKI_W", "W_RAUMA_W"),
    ("W_RAUMA_W", "W_PORI_W"), ("W_RAUMA_W", "W_BOTH_MW"), ("W_PORI_W", "W_BOTH_ME"),
    ("W_PORI_W", "W_BOTH_MW"), ("W_GAVLE_E", "W_NORRSUND_E"), ("W_NORRSUND_E", "W_SANDARNE_E"),
    ("W_SANDARNE_E", "W_BOTH_MW"), ("W_SANDARNE_E", "W_SUNDSVALL_E"), ("W_BOTH_MW", "W_BOTH_ME"),
    ("W_BOTH_MW", "W_SUNDSVALL_E"), ("W_BOTH_MW", "W_KVARKEN_S"), ("W_SUNDSVALL_E", "W_KVARKEN_S"),
    ("W_BOTH_ME", "W_KRISTIINA_W"), ("W_BOTH_ME", "W_KASKINEN_W"), ("W_BOTH_ME", "W_KVARKEN_S"),
    ("W_KRISTIINA_W", "W_KASKINEN_W"), ("W_KASKINEN_W", "W_KVARKEN_S"), ("W_KVARKEN_S", "W_KVARKEN_M"),
    ("W_KVARKEN_M", "W_VAASA_W"), ("W_KVARKEN_M", "W_KVARKEN_N"), ("W_KVARKEN_M", "W_UMEA_E"),
    ("W_VAASA_W", "W_KVARKEN_N"), ("W_UMEA_E", "W_KVARKEN_N"), ("W_KVARKEN_N", "W_BAY_S"),
    ("W_BAY_S", "W_PIETAR_W"), ("W_BAY_S", "W_KOKKOLA_W"), ("W_BAY_S", "W_PITEA_E"),
    ("W_BAY_S", "W_RAAHE_W"), ("W_PIETAR_W", "W_KOKKOLA_W"), ("W_KOKKOLA_W", "W_RAAHE_W"),
    ("W_KOKKOLA_W", "W_PITEA_E"), ("W_RAAHE_W", "W_OULU_W"), ("W_RAAHE_W", "W_LULEA_E"),
    ("W_RAAHE_W", "W_PITEA_E"), ("W_PITEA_E", "W_LULEA_E"), ("W_LULEA_E", "W_OULU_W"),
    ("W_LULEA_E", "W_KEMI_S"), ("W_OULU_W", "W_OULU_CH"), ("W_OULU_W", "W_KEMI_S"),
    ("W_BOGSKAR", "W_BALT_NC"), ("W_BOGSKAR", "W_GOTSKA"), ("W_BOGSKAR", "W_LANDSORT"),
    ("W_BALT_NC", "W_GOTSKA"), ("W_BALT_NC", "W_GOTLAND_E"), ("W_BALT_NC", "W_IRBE"),
    ("W_BALT_NC", "W_VENTSPILS_W"), ("W_GOTSKA", "W_LANDSORT"), ("W_GOTSKA", "W_GOTLAND_W"),
    ("W_GOTSKA", "W_GOTLAND_E"), ("W_LANDSORT", "W_OXELO_E"), ("W_LANDSORT", "W_GOTLAND_W"),
    ("W_OXELO_E", "W_GOTLAND_W"), ("W_GOTLAND_W", "W_OLAND_S"), ("W_GOTLAND_W", "W_HOBURGEN"),
    ("W_GOTLAND_E", "W_IRBE"), ("W_GOTLAND_E", "W_VENTSPILS_W"), ("W_GOTLAND_E", "W_LIEPAJA_W"),
    ("W_GOTLAND_E", "W_HOBURGEN"), ("W_IRBE", "W_ROOMA_S"), ("W_IRBE", "W_RIGA_GULF"),
    ("W_IRBE", "W_VENTSPILS_W"), ("W_ROOMA_S", "W_RIGA_GULF"), ("W_RIGA_GULF", "W_PARNU_W"),
    ("W_VENTSPILS_W", "W_LIEPAJA_W"), ("W_VENTSPILS_W", "W_HOBURGEN"), ("W_LIEPAJA_W", "W_KLAIPEDA_W"),
    ("W_LIEPAJA_W", "W_HOBURGEN"), ("W_KLAIPEDA_W", "W_KALIN_W"), ("W_KLAIPEDA_W", "W_GDANSK_N"),
    ("W_KLAIPEDA_W", "W_HOBURGEN"), ("W_KALIN_W", "W_GDANSK_N"), ("W_GDANSK_N", "W_HOBURGEN"),
    ("W_GDANSK_N", "W_BORNHOLM_S"), ("W_GDANSK_N", "W_BORNHOLM_N"), ("W_HOBURGEN", "W_OLAND_S"),
    ("W_HOBURGEN", "W_BORNHOLM_N"), ("W_HOBURGEN", "W_BORNHOLM_S"), ("W_OLAND_S", "W_BORNHOLM_N"),
    ("W_BORNHOLM_N", "W_BORNHOLM_S"), ("W_BORNHOLM_N", "W_FALSTERBO"), ("W_BORNHOLM_N", "W_ARKONA"),
    ("W_BORNHOLM_S", "W_SWINO_N"), ("W_BORNHOLM_S", "W_ARKONA"), ("W_SWINO_N", "W_ARKONA"),
    ("W_ARKONA", "W_FALSTERBO"), ("W_ARKONA", "W_DARSS"), ("W_DARSS", "W_FALSTERBO"),
    ("W_DARSS", "W_ROSTOCK_N"), ("W_DARSS", "W_FEHMARN"), ("W_ROSTOCK_N", "W_FEHMARN"),
    ("W_FEHMARN", "W_LUBECK_BAY"), ("W_FEHMARN", "W_KIEL_BIGHT"),
    ("W_KIEL_BIGHT", "W_KIEL_WEST"), ("W_KIEL_WEST", "W_ELBE_OUT"), ("W_FALSTERBO", "W_SOUND"),
    ("W_SOUND", "W_KATTEGAT"), ("W_KATTEGAT", "W_GOTEBORG_W"), ("W_KATTEGAT", "W_SKAGEN"),
    ("W_GOTEBORG_W", "W_SKAGEN"), ("W_SKAGEN", "W_SKAGERRAK"), ("W_SKAGERRAK", "W_ELBE_OUT"),
    ("W_SKAGERRAK", "W_HELGOLAND"), ("W_SKAGERRAK", "W_TEXEL"), ("W_SKAGERRAK", "W_NORWAY_SW"),
    ("W_ELBE_OUT", "W_HELGOLAND"), ("W_HELGOLAND", "W_TEXEL"), ("W_TEXEL", "W_EUROPOORT"),
    ("W_EUROPOORT", "W_SCHELDT"), ("W_SCHELDT", "W_DOVER"), ("W_DOVER", "W_USHANT"),
    ("W_USHANT", "W_FINISTERRE"), ("W_FINISTERRE", "W_ST_VINCENT"), ("W_ST_VINCENT", "W_GIBRALTAR"),
    ("W_GIBRALTAR", "W_MED_W"), ("W_MED_W", "W_SICILY"), ("W_SICILY", "W_CRETE_S"),
    ("W_CRETE_S", "W_AEGEAN"), ("W_CRETE_S", "W_MED_E"), ("W_NORWAY_SW", "W_NORWAY_MID"),
    ("W_NORWAY_MID", "W_LOFOTEN"), ("W_LOFOTEN", "W_NORTHCAPE"),
]

PORT_APPROACHES = {
    "FIHEL": "W_HARMAJA", "FIVSS": "W_VUOSAARI_S", "FIHKO": "W_RUSSARO", "FITKU": "W_AIRISTO",
    "FINLI": "W_NAANTALI_S", "FIMHQ": "W_MARIEHAMN_S", "FILAN": "W_LANGNAS_E", "FIECK": "W_ECKERO_W",
    "FIKTK": "W_KOTKA_S", "FIHMN": "W_HAMINA_S", "FIINK": "W_INKOO_S", "FIVKO": "W_LOVIISA_S",
    "FIRAU": "W_RAUMA_W", "FIPOR": "W_PORI_W", "FIVAA": "W_VAASA_W", "FIKOK": "W_KOKKOLA_W",
    "FIPRS": "W_PIETAR_W", "FIRAA": "W_RAAHE_W", "FIOUL": "W_OULU_CH", "FIKEM": "W_KEMI_S",
    "FITOR": "W_KEMI_S", "FIKAS": "W_KASKINEN_W", "FIUKI": "W_UKI_W", "FIPAR": "W_PARAINEN_S",
    "FIFOR": "W_FORBY_W", "FISKV": "W_SKOLDVIK_S", "FIKRS": "W_KRISTIINA_W", "FISAL": "W_SALO_S",
    "FITEI": "W_SALO_S", "FIKUS": "W_KUSTAVI_W", "EETLL": "W_TALLINN_BAY", "EEVAN": "W_TALLINN_BAY",
    "EEMUG": "W_MUUGA_N", "EEPLS": "W_PALDISKI_N", "EESLM": "W_SILLAMAE_N", "EERMS": "W_ROOMA_S",
    "EEPRN": "W_PARNU_W", "SESTO": "W_VAXHOLM", "SEKAP": "W_KAPELL_E", "SEKPS": "W_KAPELL_E",
    "SEGRH": "W_GRISSLE_E", "SEGOT": "W_GOTEBORG_W", "SEPIT": "W_PITEA_E", "SENOT": "W_NORRSUND_E",
    "SESSR": "W_SANDARNE_E", "SEGVX": "W_GAVLE_E", "SELUL": "W_LULEA_E", "SEUME": "W_UMEA_E",
    "SESDL": "W_SUNDSVALL_E", "SENYN": "W_LANDSORT", "SEOXE": "W_OXELO_E", "SENRK": "W_OXELO_E",
    "RUULU": "W_USTLUGA_N", "RULED": "W_SPB_CH", "RUPRI": "W_PRIMORSK_S", "RUVYS": "W_VYSOTSK_S",
    "RUKGD": "W_KALIN_W", "RUKLD": "W_KALIN_W", "RUMMK": "W_NORTHCAPE", "DETRV": "W_LUBECK_BAY",
    "DERSK": "W_ROSTOCK_N", "DEKEL": "W_KIEL_BIGHT", "DELBC": "W_LUBECK_BAY", "DEBRB": "W_KIEL_WEST",
    "DEWVN": "W_ELBE_OUT", "DEHAM": "W_ELBE_OUT", "DEBRV": "W_ELBE_OUT", "PLGDY": "W_GDANSK_N",
    "PLGDN": "W_GDANSK_N", "PLSWI": "W_SWINO_N", "PLSZZ": "W_SWINO_N", "LVRIX": "W_RIGA_GULF",
    "LVVNT": "W_VENTSPILS_W", "LVLPX": "W_LIEPAJA_W", "LTKLJ": "W_KLAIPEDA_W", "NLRTM": "W_EUROPOORT",
    "NLAMS": "W_TEXEL", "NLVLI": "W_SCHELDT", "NLMOE": "W_EUROPOORT", "BEANR": "W_SCHELDT",
    "BEZEE": "W_SCHELDT", "TRISK": "W_MED_E", "TRALI": "W_AEGEAN", "EGPSD": "W_MED_E",
    "EGSUZ": "W_MED_E", "ELDAB": "W_MED_E", "GIGIB": "W_GIBRALTAR", "NOGLO": "W_LOFOTEN",
    "NOMON": "W_NORWAY_SW", "PACTB": "W_GIBRALTAR",
}


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def bearing_deg(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def angle_diff(a, b):
    d = abs(a - b) % 360
    return 360 - d if d > 180 else d


def offset_latlon(lat, lon, dist_km, brg_deg):
    brg = math.radians(brg_deg)
    d_lat = (dist_km / 111.32) * math.cos(brg)
    d_lon = (dist_km / (111.32 * max(0.2, math.cos(math.radians(lat))))) * math.sin(brg)
    return [round(lat + d_lat, 5), round(lon + d_lon, 5)]


# Build adjacency list & precompute all-pairs shortest paths on SEA_NODES
SEA_ADJ = {k: [] for k in SEA_NODES}
for _u, _v in SEA_EDGES:
    _w = haversine_km(SEA_NODES[_u][0], SEA_NODES[_u][1], SEA_NODES[_v][0], SEA_NODES[_v][1])
    SEA_ADJ[_u].append((_v, _w))
    SEA_ADJ[_v].append((_u, _w))


@functools.lru_cache(maxsize=None)
def find_sea_node_path(start_node, end_node):
    """Dijkstra shortest path on the sea-lane graph (cached; graph is static)."""
    if start_node == end_node:
        return (start_node,), 0.0
    pq = [(0.0, start_node)]
    dists = {start_node: 0.0}
    prev = {}
    while pq:
        d, u = heapq.heappop(pq)
        if u == end_node:
            break
        if d > dists.get(u, float("inf")):
            continue
        for v, w in SEA_ADJ.get(u, []):
            nd = d + w
            if nd < dists.get(v, float("inf")):
                dists[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    if end_node not in dists:
        return (start_node, end_node), haversine_km(*SEA_NODES[start_node], *SEA_NODES[end_node])
    path = []
    cur = end_node
    while cur:
        path.append(cur)
        cur = prev.get(cur)
    path.reverse()
    return tuple(path), dists[end_node]


def nearest_sea_node(lat, lon):
    best_k = "W_HARMAJA"
    best_d = float("inf")
    for k, (nlat, nlon) in SEA_NODES.items():
        d = haversine_km(lat, lon, nlat, nlon)
        if d < best_d:
            best_d = d
            best_k = k
    return best_k, best_d


def port_approach_node(port):
    code = port.get("code", "")
    if code in PORT_APPROACHES:
        return PORT_APPROACHES[code]
    k, _ = nearest_sea_node(port["lat"], port["lon"])
    return k


def chaikin_smooth(pts, iterations=2):
    if len(pts) <= 2:
        return pts
    res = pts
    for _ in range(iterations):
        new_pts = [res[0]]
        for i in range(len(res) - 1):
            p0, p1 = res[i], res[i + 1]
            q = [round(0.75 * p0[0] + 0.25 * p1[0], 5), round(0.75 * p0[1] + 0.25 * p1[1], 5)]
            r = [round(0.25 * p0[0] + 0.75 * p1[0], 5), round(0.25 * p0[1] + 0.75 * p1[1], 5)]
            new_pts.extend([q, r])
        new_pts.append(res[-1])
        res = new_pts
    return res


def build_maritime_fairway_route(port, ship_lat, ship_lon, course=None, is_origin=True):
    """Builds a realistic curved maritime fairway path between a harbour and a vessel position."""
    p_lat, p_lon = port["lat"], port["lon"]
    direct_km = haversine_km(p_lat, p_lon, ship_lat, ship_lon)

    # If the ship is moored inside this harbour (< 0.8 km), return minimal path
    if direct_km < 0.8:
        return [[p_lat, p_lon], [ship_lat, ship_lon]], direct_km

    app_node = port_approach_node(port)
    app_lat, app_lon = SEA_NODES[app_node]

    # Candidate sea nodes near the ship (top 3 closest)
    cand = sorted(
        SEA_NODES.keys(),
        key=lambda k: haversine_km(ship_lat, ship_lon, SEA_NODES[k][0], SEA_NODES[k][1]),
    )[:3]

    best_node_seq = None
    best_total_km = float("inf")
    for c_node in cand:
        seq, graph_km = find_sea_node_path(app_node, c_node)
        ship_to_c = haversine_km(ship_lat, ship_lon, *SEA_NODES[c_node])
        tot = haversine_km(p_lat, p_lon, app_lat, app_lon) + graph_km + ship_to_c
        if tot < best_total_km:
            best_total_km = tot
            best_node_seq = seq

    coords = [[p_lat, p_lon]]
    for nk in best_node_seq:
        coords.append([SEA_NODES[nk][0], SEA_NODES[nk][1]])

    # Avoid overshooting the ship if the last sea node goes past the ship and backtracks
    while len(coords) >= 2:
        prev_pt = coords[-2]
        last_node_pt = coords[-1]
        d_prev_ship = haversine_km(prev_pt[0], prev_pt[1], ship_lat, ship_lon)
        d_prev_last = haversine_km(prev_pt[0], prev_pt[1], last_node_pt[0], last_node_pt[1])
        turn = angle_diff(
            bearing_deg(prev_pt[0], prev_pt[1], last_node_pt[0], last_node_pt[1]),
            bearing_deg(last_node_pt[0], last_node_pt[1], ship_lat, ship_lon),
        )
        if d_prev_ship < d_prev_last or turn > 95:
            coords.pop()
        else:
            break

    # If the ship is between the harbour and the first fairway node, add harbour channel & course-aligned waypoints
    if len(coords) == 1:
        ch_brg = bearing_deg(p_lat, p_lon, app_lat, app_lon)
        ch_dist = min(direct_km * 0.38, haversine_km(p_lat, p_lon, app_lat, app_lon) * 0.65)
        if ch_dist > 0.35:
            coords.append(offset_latlon(p_lat, p_lon, ch_dist, ch_brg))

    # Add a wake/bow alignment control point near the ship so the route curves smoothly into the ship's heading
    last_w = coords[-1]
    leg_km = haversine_km(last_w[0], last_w[1], ship_lat, ship_lon)
    if course is not None and leg_km > 1.2:
        align_brg = ((course + 180) % 360) if is_origin else course
        ctrl_dist = min(leg_km * 0.35, 10.0)
        ctrl_pt = offset_latlon(ship_lat, ship_lon, ctrl_dist, align_brg)
        if haversine_km(last_w[0], last_w[1], ctrl_pt[0], ctrl_pt[1]) < leg_km * 1.15:
            coords.append(ctrl_pt)
    elif leg_km > 2.0 and len(coords) < 3:
        # Gentle fairway channel offset perpendicular to chord so it never looks like a ruler line
        mid_lat = (last_w[0] + ship_lat) / 2.0
        mid_lon = (last_w[1] + ship_lon) / 2.0
        brg = bearing_deg(last_w[0], last_w[1], ship_lat, ship_lon)
        perp_pt = offset_latlon(mid_lat, mid_lon, min(leg_km * 0.14, 3.5), (brg + 90) % 360)
        coords.append(perp_pt)

    coords.append([ship_lat, ship_lon])
    if not is_origin:
        coords.reverse()

    smoothed = chaikin_smooth(coords, iterations=2)
    return smoothed, best_total_km


def init_custom_ports():
    for code, info in CUSTOM_PORTS.items():
        ports_by_code[code] = info
        ports_by_name[info["name"].upper()] = info
        base = re.sub(r"\s*\(.*?\)", "", info["name"]).strip().upper()
        if base:
            ports_by_name[base] = info
    for alias, code in NAME_ALIASES.items():
        if code in CUSTOM_PORTS:
            ports_by_name[alias.upper()] = CUSTOM_PORTS[code]


init_custom_ports()


def categorize_vessel(code):
    if 70 <= code <= 89:
        return "Cargo"
    if (60 <= code <= 69) or code in [40, 50]:
        return "Commercial"
    if code in [36, 37]:
        return "Private"
    return "Other"


def get_ship_type_name(code):
    if not code:
        return "Unknown"
    if code == 31:
        return "Tug"
    if code == 32:
        return "Sailing"
    if 30 <= code <= 39:
        return "Fishing"
    if 40 <= code <= 49:
        return "High Speed Craft"
    if 50 <= code <= 59:
        return "Special Craft"
    if 60 <= code <= 69:
        return "Passenger"
    if 70 <= code <= 79:
        return "Cargo"
    if 80 <= code <= 89:
        return "Tanker"
    return f"Type {code}"


def decode_ais_eta(raw_eta):
    """Decodes 20-bit AIS ETA integer into 'YYYY-MM-DD HH:MM UTC' if valid and not stale."""
    if not raw_eta or not isinstance(raw_eta, int):
        return None
    month = (raw_eta >> 16) & 0x0F
    day = (raw_eta >> 11) & 0x1F
    hour = (raw_eta >> 6) & 0x1F
    minute = raw_eta & 0x3F
    if month < 1 or month > 12 or day < 1 or day > 31:
        return None
    now = datetime.datetime.now(datetime.timezone.utc)
    h = 0 if hour >= 24 else hour
    m = 0 if minute >= 60 else minute
    # AIS ETA has no year: pick the candidate year closest to now
    best = None
    for year in (now.year - 1, now.year, now.year + 1):
        try:
            cand = datetime.datetime(year, month, day, h, m, tzinfo=datetime.timezone.utc)
        except ValueError:
            continue
        if best is None or abs((cand - now).total_seconds()) < abs((best - now).total_seconds()):
            best = cand
    if best is None:
        return None
    # Only trust ETAs from 36 h ago up to 45 days ahead (older/further ones are stale or placeholders)
    delta = (best - now).total_seconds()
    if delta < -36 * 3600 or delta > 45 * 86400:
        return None
    return best.strftime("%Y-%m-%d %H:%M UTC")


def format_iso_eta(iso_str):
    if not iso_str:
        return None
    try:
        dt = datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.datetime.now(datetime.timezone.utc)
        if (now - dt).total_seconds() > 36 * 3600:
            return None
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return None


def fetch_ports_catalog():
    try:
        logger.info("Fetching ports catalog...")
        resp = requests.get(MARINE_PORTS_URL, headers=HEADERS, timeout=25)
        if resp.status_code == 200:
            ssn = resp.json().get("ssnLocations", {}).get("features", [])
            for f in ssn:
                geom = f.get("geometry")
                if geom and geom.get("coordinates"):
                    lon, lat = geom["coordinates"]
                    code = (f["properties"].get("locode") or "").upper()
                    name = (f["properties"].get("locationName") or "").strip()
                    if code and code not in CUSTOM_PORTS:
                        ports_by_code[code] = {"code": code, "name": name or code, "lat": lat, "lon": lon}
                    if name:
                        entry = ports_by_code.get(code) or {"code": code, "name": name, "lat": lat, "lon": lon}
                        if name.upper() not in ports_by_name:
                            ports_by_name[name.upper()] = entry
                        base = re.sub(r"\s*\(.*?\)", "", name).strip().upper()
                        if base and base not in ports_by_name:
                            ports_by_name[base] = entry
        w_resp = requests.get(MARINE_WINTER_PORTS_URL, headers=HEADERS, timeout=15)
        if w_resp.status_code == 200:
            for f in w_resp.json().get("features", []):
                geom = f.get("geometry")
                if geom and geom.get("coordinates"):
                    lon, lat = geom["coordinates"]
                    code = (f["properties"].get("locodeList") or "").upper()
                    name = (f["properties"].get("name") or "").strip().title()
                    if code and code not in ports_by_code:
                        ports_by_code[code] = {"code": code, "name": name or code, "lat": lat, "lon": lon}
                    if name and name.upper() not in ports_by_name:
                        ports_by_name[name.upper()] = ports_by_code.get(code) or {
                            "code": code or name[:5].upper(),
                            "name": name,
                            "lat": lat,
                            "lon": lon,
                        }
        init_custom_ports()
        logger.info(f"Loaded {len(ports_by_code)} ports with coordinates.")
    except Exception as e:
        logger.error(f"Error loading ports catalog: {e}")


def fetch_port_calls_once():
    global port_calls_by_mmsi
    try:
        resp = requests.get(MARINE_PORT_CALLS_URL, headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            pcs = resp.json().get("portCalls", [])
            mapping = {}
            for pc in pcs:
                mmsi = str(pc.get("mmsi") or "")
                if not mmsi:
                    continue
                details = pc.get("portAreaDetails") or [{}]
                d0 = details[0] if details else {}
                mapping[mmsi] = {
                    "portToVisit": (pc.get("portToVisit") or "").strip().upper(),
                    "prevPort": (pc.get("prevPort") or "").strip().upper(),
                    "nextPort": (pc.get("nextPort") or "").strip().upper(),
                    "eta": d0.get("eta"),
                    "ata": d0.get("ata"),
                    "atd": d0.get("atd"),
                    "etd": d0.get("etd"),
                }
            port_calls_by_mmsi = mapping
            logger.info(f"Loaded port calls for {len(port_calls_by_mmsi)} vessels.")
    except Exception as e:
        logger.error(f"Error fetching port calls: {e}")


def fetch_marine_metadata_once():
    global vessels_metadata
    try:
        logger.info("Fetching marine metadata...")
        resp = requests.get(MARINE_META_URL, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            new_meta = {}
            for v in data:
                mmsi = str(v.get("mmsi"))
                if not mmsi:
                    continue
                ship_code = v.get("shipType", 0)
                new_meta[mmsi] = {
                    "name": (v.get("name") or "Unknown").strip() or "Unknown",
                    "shipType": v.get("shipTypeEn") or get_ship_type_name(ship_code),
                    "category": categorize_vessel(ship_code),
                    "callSign": (v.get("callSign") or "N/A").strip() or "N/A",
                    "destination": (v.get("destination") or "").strip(),
                    "etaRaw": v.get("eta", 0),
                }
            vessels_metadata = new_meta
            logger.info(f"Metadata updated for {len(vessels_metadata)} vessels.")
            return True
    except Exception as e:
        logger.error(f"Meta Error: {e}")
    return False


def metadata_update_loop():
    fetch_ports_catalog()
    fetch_marine_metadata_once()
    fetch_port_calls_once()
    socketio.start_background_task(fetch_marine_data)
    while True:
        socketio.sleep(600)
        fetch_marine_metadata_once()
        fetch_port_calls_once()


def resolve_port_token(token):
    if not token:
        return None
    t = token.strip().upper()
    t = re.sub(r"\s+VIA\s+.*$", "", t)
    t = re.sub(r"\(.*?\)", "", t)
    t = re.sub(r"\bANCH.*$", "", t)
    t = re.sub(r"\bAREA.*$", "", t).strip(" ><=-_.,:")
    if not t or t in ("N/A", "UNKNOWN", "FOR ORDERS", "FOR ORDER", "TO ORDER", "TBA"):
        return None
    if t in NAME_ALIASES:
        return ports_by_code.get(NAME_ALIASES[t])
    if t in ports_by_code:
        return ports_by_code[t]
    compact = t.replace(" ", "").replace("-", "").replace("_", "")
    if len(compact) == 5 and compact in ports_by_code:
        return ports_by_code[compact]
    if compact in NAME_ALIASES:
        return ports_by_code.get(NAME_ALIASES[compact])
    if t in ports_by_name:
        return ports_by_name[t]
    for alias, code in NAME_ALIASES.items():
        if len(alias) >= 4 and alias in t:
            return ports_by_code.get(code)
    return None


def parse_ais_destination_ports(raw_dest):
    if not raw_dest:
        return None, None
    cleaned = raw_dest.strip().upper()
    if any(sep in cleaned for sep in [">", "<", "/", "->"]):
        parts = [p.strip() for p in re.split(r"[<>=/]+|->", cleaned) if p.strip()]
        resolved = [resolve_port_token(p) for p in parts]
        resolved = [r for r in resolved if r is not None]
        if len(resolved) >= 2:
            return resolved[0], resolved[-1]
        elif len(resolved) == 1:
            return None, resolved[0]
    m = re.match(r"^([A-Z]{2}\s?[A-Z]{3})\s*-\s*([A-Z]{2}\s?[A-Z]{3})$", cleaned)
    if m:
        p1 = resolve_port_token(m.group(1))
        p2 = resolve_port_token(m.group(2))
        if p1 or p2:
            return p1, p2
    return None, resolve_port_token(cleaned)


def infer_harbour_from_position(lat, lon, course=None, exclude_code=None, reverse=True):
    """Finds the most plausible Baltic harbour along the maritime fairway network."""
    best_port = None
    best_score = float("inf")
    target_bearing = ((course + 180) % 360) if (course is not None and reverse) else course
    ship_node, ship_node_dist = nearest_sea_node(lat, lon)

    for code in BALTIC_HUB_CODES:
        if code == exclude_code:
            continue
        p = ports_by_code.get(code)
        if not p:
            continue
        direct_dist = haversine_km(lat, lon, p["lat"], p["lon"])
        if direct_dist < 6.0 and reverse:
            return p
        p_node = port_approach_node(p)
        _, graph_km = find_sea_node_path(ship_node, p_node)
        sea_dist = ship_node_dist + graph_km + haversine_km(p["lat"], p["lon"], *SEA_NODES[p_node])
        score = sea_dist
        if target_bearing is not None and direct_dist > 5.0:
            b = bearing_deg(lat, lon, p["lat"], p["lon"])
            diff = angle_diff(target_bearing, b)
            score = sea_dist * (1.0 + (diff / 95.0) ** 1.4)
        if score < best_score:
            best_score = score
            best_port = p
    return best_port or CUSTOM_PORTS["FIHEL"]


def enrich_vessel_route_and_eta(mmsi, lat, lon, speed, course, meta):
    raw_dest = (meta.get("destination") or "").strip()
    pc = port_calls_by_mmsi.get(mmsi)

    origin_port = None
    dest_port = None
    eta_str = None

    if pc:
        prev_p = resolve_port_token(pc.get("prevPort"))
        visit_p = resolve_port_token(pc.get("portToVisit"))
        next_p = resolve_port_token(pc.get("nextPort"))

        if pc.get("atd"):
            origin_port = visit_p or prev_p
            dest_port = next_p
        else:
            origin_port = prev_p
            dest_port = visit_p
            eta_str = format_iso_eta(pc.get("eta"))

    ais_orig, ais_dest = parse_ais_destination_ports(raw_dest)
    if ais_orig and ais_dest and course is not None:
        b_to_dest = bearing_deg(lat, lon, ais_dest["lat"], ais_dest["lon"])
        b_to_orig = bearing_deg(lat, lon, ais_orig["lat"], ais_orig["lon"])
        if angle_diff(course, b_to_orig) + 15 < angle_diff(course, b_to_dest):
            ais_orig, ais_dest = ais_dest, ais_orig

    if not origin_port and ais_orig:
        origin_port = ais_orig
    if not dest_port and ais_dest:
        dest_port = ais_dest

    if not dest_port:
        dest_port = infer_harbour_from_position(
            lat, lon, course=course, exclude_code=origin_port["code"] if origin_port else None, reverse=False
        )

    if not origin_port or (dest_port and origin_port["code"] == dest_port["code"]):
        if mmsi in vessel_origins and vessel_origins[mmsi]["code"] != dest_port["code"]:
            origin_port = vessel_origins[mmsi]
        else:
            start_lat, start_lon = vessel_trails.get(mmsi, [[lat, lon]])[0]
            origin_port = infer_harbour_from_position(
                start_lat,
                start_lon,
                course=course,
                exclude_code=dest_port["code"] if dest_port else None,
                reverse=True,
            )
            vessel_origins[mmsi] = origin_port

    # Build maritime fairway route from departure harbour -> ship's initial trail point -> live trail
    trail = vessel_trails.get(mmsi, [[lat, lon]])
    fairway_to_ship, _ = build_maritime_fairway_route(
        origin_port, trail[0][0], trail[0][1], course=course, is_origin=True
    )
    full_route = fairway_to_ship + trail[1:]

    # Build maritime fairway route from ship's current position -> destination harbour
    dest_route, rem_sea_km = build_maritime_fairway_route(
        dest_port, lat, lon, course=course, is_origin=False
    )

    if not eta_str:
        eta_str = decode_ais_eta(meta.get("etaRaw"))
    if not eta_str and dest_port:
        dist_km = max(haversine_km(lat, lon, dest_port["lat"], dest_port["lon"]), rem_sea_km * 0.85)
        speed_kmh = (speed or 0) * 1.852
        if haversine_km(lat, lon, dest_port["lat"], dest_port["lon"]) < 3.0 or speed_kmh < 1.0:
            eta_str = (
                "Arrived / At Harbour"
                if haversine_km(lat, lon, dest_port["lat"], dest_port["lon"]) < 5.0
                else "Moored / Stationary"
            )
        else:
            hours = dist_km / speed_kmh
            if hours < 360:
                arr_dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=hours)
                eta_str = arr_dt.strftime("Est. %Y-%m-%d %H:%M UTC")
            else:
                eta_str = "N/A"

    return origin_port, dest_port, eta_str or "N/A", full_route, dest_route


def fetch_marine_data():
    global latest_data_cache, latest_stats_cache
    while True:
        try:
            resp = requests.get(MARINE_LOC_URL, headers=HEADERS, timeout=20)
            if resp.status_code == 200:
                features = resp.json().get("features", [])
                enriched = []
                for feat in features:
                    props = feat.get("properties", {})
                    mmsi = str(props.get("mmsi"))
                    lat = feat["geometry"]["coordinates"][1]
                    lon = feat["geometry"]["coordinates"][0]
                    meta = vessels_metadata.get(mmsi, {})

                    speed = props.get("sog", 0) or 0
                    raw_heading = props.get("heading")
                    cog = props.get("cog")
                    if raw_heading is not None and raw_heading != 511 and 0 <= raw_heading <= 360:
                        heading = raw_heading
                    elif cog is not None and 0 <= cog <= 360:
                        heading = round(cog)
                    else:
                        heading = "N/A"

                    course = heading if isinstance(heading, (int, float)) else None

                    trail = vessel_trails.get(mmsi)
                    if not trail:
                        trail = [[lat, lon]]
                        vessel_trails[mmsi] = trail
                    else:
                        last_lat, last_lon = trail[-1]
                        if abs(lat - last_lat) > 0.00012 or abs(lon - last_lon) > 0.00012:
                            trail.append([lat, lon])
                            if len(trail) > 150:
                                trail.pop(0)

                    origin_port, dest_port, eta_str, full_route, dest_route = enrich_vessel_route_and_eta(
                        mmsi, lat, lon, speed, course, meta
                    )

                    enriched.append({
                        "mmsi": mmsi,
                        "lat": lat,
                        "lon": lon,
                        "name": meta.get("name", "Unknown Vessel"),
                        "shipType": meta.get("shipType", "Unknown"),
                        "category": meta.get("category", "Other"),
                        "speed": speed,
                        "heading": heading,
                        "timestamp": props.get("timestampExternal", "N/A"),
                        "callSign": meta.get("callSign", "N/A"),
                        "origin": origin_port["name"],
                        "originCode": origin_port["code"],
                        "originLat": origin_port["lat"],
                        "originLon": origin_port["lon"],
                        "destination": dest_port["name"],
                        "destCode": dest_port["code"],
                        "destLat": dest_port["lat"],
                        "destLon": dest_port["lon"],
                        "rawDestination": meta.get("destination") or dest_port["name"],
                        "eta": eta_str,
                        "route": full_route,
                        "destRoute": dest_route,
                    })

                enriched.sort(
                    key=lambda x: (
                        x["name"] == "Unknown Vessel",
                        0 if x["speed"] > 0.5 else 1,
                        -x["speed"],
                    )
                )
                latest_data_cache = enriched

                now_str = datetime.datetime.now().strftime("%H:%M:%S")
                history_data["times"].append(now_str)
                history_data["counts"].append(len(enriched))
                if len(history_data["times"]) > 60:
                    history_data["times"].pop(0)
                    history_data["counts"].pop(0)

                speeds = [v.get("speed", 0) for v in enriched if v.get("speed", 0) > 0]
                avg_speed = sum(speeds) / len(speeds) if speeds else 0
                max_speed = max(speeds) if speeds else 0
                categories = {}
                for v in enriched:
                    c = v.get("category", "Other")
                    categories[c] = categories.get(c, 0) + 1

                latest_stats_cache = {
                    "total": len(enriched),
                    "avg_speed": round(avg_speed * 1.852, 1),
                    "max_speed": round(max_speed * 1.852, 1),
                    "categories": categories,
                    "history": history_data,
                }

                socketio.emit("marine_locations", enriched)
                socketio.emit("marine_statistics", latest_stats_cache)
                logger.info(f"Emitted {len(enriched)} vessels and stats.")
        except Exception as e:
            logger.error(f"Data Error: {e}")
        socketio.sleep(FETCH_INTERVAL)


@socketio.on("connect")
def handle_connect():
    if latest_data_cache:
        socketio.emit("marine_locations", latest_data_cache, to=request.sid)
    if latest_stats_cache:
        socketio.emit("marine_statistics", latest_stats_cache, to=request.sid)


@app.route("/")
def index():
    return render_template("marine_index.html")


@app.route("/shutdown", methods=["POST"])
def shutdown():
    logger.info("Shutdown requested.")

    def kill():
        time.sleep(2)
        os._exit(0)

    threading.Thread(target=kill).start()
    return "Shutting down Marine Tracker..."


if __name__ == "__main__":
    socketio.start_background_task(metadata_update_loop)
    port = 5003
    logger.info(f"Starting Marine Tracker on port {port}...")
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
