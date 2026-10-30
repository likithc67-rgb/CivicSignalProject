"""Insert 36 synthetic demo reports. Safe to run more than once."""
import sqlite3
from datetime import datetime, timedelta
from app import DB_PATH, init_db, insert_report

SAMPLES = [
("Large pothole near the bus stop causing vehicles to swerve", "Road Damage", "MG Road Junction", 12.9758,77.6050),
("Deep pothole on MG Road near the bus stop, two-wheelers are swerving", "Road Damage", "MG Road Junction", 12.9759,77.6051),
("Rain water has collected on the road and pedestrians cannot cross", "Waterlogging", "Indiranagar 100 Feet Road", 12.9784,77.6408),
("Severe waterlogging after rain near the school entrance", "Waterlogging", "Indiranagar 100 Feet Road", 12.9785,77.6407),
("Garbage bins are overflowing and waste is scattered on the footpath", "Waste Management", "Jayanagar 4th Block", 12.9250,77.5838),
("Overflowing dustbin creating bad smell near market", "Waste Management", "Jayanagar 4th Block", 12.9251,77.5839),
("Street light is not working; the road is dark at night", "Streetlight", "BTM Layout 2nd Stage", 12.9166,77.6101),
("Several streetlights are off near the park entrance", "Streetlight", "BTM Layout 2nd Stage", 12.9167,77.6102),
("Drain is blocked and dirty water is flowing onto the street", "Drainage", "HSR Sector 2", 12.9116,77.6474),
("Blocked drainage causing sewage to overflow near houses", "Drainage", "HSR Sector 2", 12.9117,77.6475),
("Open manhole on the main road is a serious danger to pedestrians", "Public Safety", "Koramangala 5th Block", 12.9345,77.6180),
("Live electric wire hanging low near a busy school crossing", "Public Safety", "Malleshwaram 8th Cross", 13.0067,77.5700),
("No drinking water supply for two days in our street", "Water Supply", "Vijayanagar", 12.9719,77.5350),
("Water pipeline leak wasting clean water continuously", "Water Supply", "Rajajinagar", 13.0108,77.5550),
("Road surface is broken and creates traffic congestion", "Road Damage", "Whitefield Main Road", 12.9698,77.7500),
("Potholes are damaging vehicles near the junction", "Road Damage", "Whitefield Main Road", 12.9699,77.7501),
("Garbage not collected for three days near apartment gate", "Waste Management", "Marathahalli", 12.9591,77.6974),
("Public bin is full and trash is lying around", "Waste Management", "Marathahalli", 12.9592,77.6975),
("Drain cover is missing and could cause an accident", "Public Safety", "Electronic City Phase 1", 12.8452,77.6602),
("Water is flooding the service road after heavy rain", "Waterlogging", "Electronic City Phase 1", 12.8453,77.6603),
("Broken footpath makes walking difficult for senior citizens", "Road Damage", "Basavanagudi", 12.9435,77.5680),
("Street lamp flickers and switches off every evening", "Streetlight", "Basavanagudi", 12.9436,77.5681),
("Sewage smell coming from the blocked storm water drain", "Drainage", "Yelahanka", 13.1007,77.5963),
("Water supply has stopped in the entire lane", "Water Supply", "Yelahanka", 13.1008,77.5964),
("A tree branch has fallen and blocks half of the road", "Public Safety", "Malleshwaram", 13.0060,77.5680),
("Road has multiple potholes and needs urgent repair", "Road Damage", "Malleshwaram", 13.0061,77.5681),
("Waste collection vehicle skipped our street this morning", "Waste Management", "Hebbal", 13.0358,77.5970),
("Large garbage pile attracting stray animals", "Waste Management", "Hebbal", 13.0359,77.5971),
("Flood water entered shops because roadside drain is clogged", "Waterlogging", "KR Market", 12.9630,77.5760),
("Manhole is overflowing with sewage near the bus stand", "Drainage", "KR Market", 12.9631,77.5761),
("No street lighting on the pedestrian walkway", "Streetlight", "Bellandur", 12.9250,77.6760),
("Dangerous open manhole beside a busy road", "Public Safety", "Bellandur", 12.9251,77.6761),
("Water pipe is leaking onto the road since yesterday", "Water Supply", "Banashankari", 12.9255,77.5460),
("Rain water stagnation is making the road slippery", "Waterlogging", "Banashankari", 12.9256,77.5461),
("Pothole filled with rainwater is difficult to notice by drivers", "Road Damage", "Banashankari", 12.9257,77.5462),
("Streetlight pole damaged after a storm", "Streetlight", "Kengeri", 12.9177,77.4830),
]

def main():
    init_db()
    db = sqlite3.connect(DB_PATH)
    count = db.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
    db.close()
    if count:
        print(f"Database already contains {count} reports. Seed skipped to avoid duplicates.")
        return
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    for i, (desc, cat, loc, lat, lon) in enumerate(SAMPLES):
        insert_report(db, {
            "title": desc[:65], "description": desc, "category": cat,
            "location": loc, "latitude": lat, "longitude": lon,
            "citizen_name": "Synthetic Demo Citizen"
        })
    db.close()
    print(f"Inserted {len(SAMPLES)} synthetic reports.")

if __name__ == "__main__":
    main()
