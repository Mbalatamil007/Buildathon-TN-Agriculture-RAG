"""Canonical district names, bilingual labels and strict metadata filtering."""
ALL_DISTRICTS = 'All districts'
DISTRICTS = {
 'Ariyalur':'அரியலூர்','Chengalpattu':'செங்கல்பட்டு','Chennai':'சென்னை',
 'Coimbatore':'கோயம்புத்தூர்','Cuddalore':'கடலூர்','Dharmapuri':'தருமபுரி',
 'Dindigul':'திண்டுக்கல்','Erode':'ஈரோடு','Kallakurichi':'கள்ளக்குறிச்சி',
 'Kancheepuram':'காஞ்சிபுரம்','Kanyakumari':'கன்னியாகுமரி','Karur':'கரூர்',
 'Krishnagiri':'கிருஷ்ணகிரி','Madurai':'மதுரை','Mayiladuthurai':'மயிலாடுதுறை',
 'Nagapattinam':'நாகப்பட்டினம்','Namakkal':'நாமக்கல்','Nilgiris':'நீலகிரி',
 'Perambalur':'பெரம்பலூர்','Pudukkottai':'புதுக்கோட்டை','Ramanathapuram':'இராமநாதபுரம்',
 'Ranipet':'இராணிப்பேட்டை','Salem':'சேலம்','Sivaganga':'சிவகங்கை',
 'Tenkasi':'தென்காசி','Thanjavur':'தஞ்சாவூர்','Theni':'தேனி','Thoothukudi':'தூத்துக்குடி',
 'Tiruchirappalli':'திருச்சிராப்பள்ளி','Tirunelveli':'திருநெல்வேலி',
 'Tirupathur':'திருப்பத்தூர்','Tiruppur':'திருப்பூர்','Tiruvallur':'திருவள்ளூர்',
 'Tiruvannamalai':'திருவண்ணாமலை','Tiruvarur':'திருவாரூர்','Vellore':'வேலூர்',
 'Viluppuram':'விழுப்புரம்','Virudhunagar':'விருதுநகர்',
}
ALIASES = {'thiruvallur':'Tiruvallur','thiruvarur':'Tiruvarur','villupuram':'Viluppuram',
 'kanniyakumari':'Kanyakumari','kanchipuram':'Kancheepuram','tirupattur':'Tirupathur',
 'tirupathur':'Tirupathur','tirupur':'Tiruppur','the nilgiris':'Nilgiris',
 'pudukottai':'Pudukkottai','trichy':'Tiruchirappalli'}

def normalize_district(value):
    value = str(value or '').strip()
    if value.casefold() in {'all', 'all districts', 'அனைத்து மாவட்டங்கள்'}:
        return ALL_DISTRICTS
    for name, tamil in DISTRICTS.items():
        if value.casefold() == name.casefold() or value == tamil:
            return name
    return ALIASES.get(value.casefold(), value)

def district_label(name):
    return 'All districts / அனைத்து மாவட்டங்கள்' if name == ALL_DISTRICTS else f'{name} / {DISTRICTS[name]}'

def validate_district(district):
    district = normalize_district(district)
    if district != ALL_DISTRICTS and district not in DISTRICTS:
        raise ValueError('Choose a district from the dropdown.')
    return district

def record_applies(metadata, district):
    district = validate_district(district)
    if district == ALL_DISTRICTS:
        return True
    # Include statewide records only when their applicability is explicit.
    if metadata.get('scope') == 'statewide':
        return True
    values = metadata.get('districts', [])
    if isinstance(values, str):
        values = [values]
    values = list(values) + [metadata.get('district', '')]
    return district in {normalize_district(value) for value in values}

def eligible_positions(documents, district):
    return [i for i, doc in enumerate(documents) if record_applies(doc.metadata, district)]
