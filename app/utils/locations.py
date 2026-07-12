INDIA_LOCATION_OPTIONS = [
    ('Andaman and Nicobar Islands', 'AN', 'Port Blair', 'PBL'),
    ('Andhra Pradesh', 'AP', 'Vijayawada', 'VJA'),
    ('Andhra Pradesh', 'AP', 'Visakhapatnam', 'VTZ'),
    ('Arunachal Pradesh', 'AR', 'Itanagar', 'ITA'),
    ('Assam', 'AS', 'Guwahati', 'GAU'),
    ('Bihar', 'BR', 'Patna', 'PAT'),
    ('Chandigarh', 'CH', 'Chandigarh', 'CHD'),
    ('Chhattisgarh', 'CG', 'Raipur', 'RPR'),
    ('Dadra and Nagar Haveli and Daman and Diu', 'DN', 'Daman', 'DAM'),
    ('Delhi', 'DL', 'Delhi', 'DEL'),
    ('Goa', 'GA', 'Panaji', 'PNJ'),
    ('Gujarat', 'GJ', 'Ahmedabad', 'AMD'),
    ('Gujarat', 'GJ', 'Surat', 'STV'),
    ('Gujarat', 'GJ', 'Vadodara', 'BDQ'),
    ('Haryana', 'HR', 'Gurugram', 'GGN'),
    ('Haryana', 'HR', 'Faridabad', 'FDB'),
    ('Himachal Pradesh', 'HP', 'Shimla', 'SML'),
    ('Jammu and Kashmir', 'JK', 'Jammu', 'JMU'),
    ('Jammu and Kashmir', 'JK', 'Srinagar', 'SXR'),
    ('Jharkhand', 'JH', 'Ranchi', 'IXR'),
    ('Karnataka', 'KA', 'Bengaluru', 'BLR'),
    ('Karnataka', 'KA', 'Mysuru', 'MYS'),
    ('Kerala', 'KL', 'Kochi', 'COK'),
    ('Kerala', 'KL', 'Thiruvananthapuram', 'TRV'),
    ('Ladakh', 'LA', 'Leh', 'IXL'),
    ('Lakshadweep', 'LD', 'Kavaratti', 'KVT'),
    ('Madhya Pradesh', 'MP', 'Bhopal', 'BHO'),
    ('Madhya Pradesh', 'MP', 'Indore', 'IDR'),
    ('Maharashtra', 'MH', 'Mumbai', 'MUM'),
    ('Maharashtra', 'MH', 'Pune', 'PUN'),
    ('Maharashtra', 'MH', 'Nagpur', 'NGP'),
    ('Maharashtra', 'MH', 'Nashik', 'NSK'),
    ('Maharashtra', 'MH', 'Thane', 'THN'),
    ('Maharashtra', 'MH', 'Navi Mumbai', 'NVM'),
    ('Manipur', 'MN', 'Imphal', 'IMF'),
    ('Meghalaya', 'ML', 'Shillong', 'SHL'),
    ('Mizoram', 'MZ', 'Aizawl', 'AJL'),
    ('Nagaland', 'NL', 'Kohima', 'KOH'),
    ('Odisha', 'OD', 'Bhubaneswar', 'BBI'),
    ('Puducherry', 'PY', 'Puducherry', 'PNY'),
    ('Punjab', 'PB', 'Ludhiana', 'LDH'),
    ('Punjab', 'PB', 'Amritsar', 'ATQ'),
    ('Rajasthan', 'RJ', 'Jaipur', 'JAI'),
    ('Rajasthan', 'RJ', 'Udaipur', 'UDR'),
    ('Sikkim', 'SK', 'Gangtok', 'GTK'),
    ('Tamil Nadu', 'TN', 'Chennai', 'MAA'),
    ('Tamil Nadu', 'TN', 'Coimbatore', 'CBE'),
    ('Telangana', 'TS', 'Hyderabad', 'HYD'),
    ('Tripura', 'TR', 'Agartala', 'IXA'),
    ('Uttar Pradesh', 'UP', 'Lucknow', 'LKO'),
    ('Uttar Pradesh', 'UP', 'Noida', 'NOI'),
    ('Uttar Pradesh', 'UP', 'Ghaziabad', 'GZB'),
    ('Uttar Pradesh', 'UP', 'Kanpur', 'KNP'),
    ('Uttarakhand', 'UK', 'Dehradun', 'DED'),
    ('West Bengal', 'WB', 'Kolkata', 'CCU'),
]

LOCATION_DETAILS_BY_NAME = {
    city.lower(): {
        'state': state,
        'state_code': state_code,
        'location': city,
        'location_code': location_code,
    }
    for state, state_code, city, location_code in INDIA_LOCATION_OPTIONS
}


def location_details_for_name(name):
    return LOCATION_DETAILS_BY_NAME.get((name or '').strip().lower())


def location_code_for_name(name):
    details = location_details_for_name(name)
    return details['location_code'] if details else None


def state_code_for_name(name):
    details = location_details_for_name(name)
    return details['state_code'] if details else None


def state_name_for_name(name):
    details = location_details_for_name(name)
    return details['state'] if details else None
