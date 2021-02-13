"""Constants settings for bouwlaag and repressief object drawing"""
import oiv.plugin_helpers.plugin_constants as PC
#repressief object constants

ROSNAPSYMBOLS = ['32', '47', '148', '150', '152', '301', 'Algemeen', 'Voorzichtig', 'Waarschuwing', 'Gevaar']
ROSNAPLAYERS = ["Object terrein", "Isolijnen", "Bereikbaarheid", "Sectoren"]
OBJECTTYPES = ['Evenement', 'Gebouw', 'Natuur', 'Waterongeval']

#bouwlaag constants
BLSNAPLAYERS = [PC.PAND["bouwlaaglayername"], PC.PAND["bagpandlayername"], "Bouwkundige veiligheidsvoorzieningen", "Ruimten"]
BLSNAPSYMBOLS = ['1', '10', '32', '47', '148', '149', '150', '151', '152',\
                 '1011', 'Algemeen', 'Voorzichtig', 'Waarschuwing', 'Gevaar']
