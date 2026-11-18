// Mock data shaped after the Group12 API (contracts/openapi.v1.json).
// Replace each export with a call to the matching endpoint when wiring the backend.

const u = (id: string, w = 800) => `https://images.unsplash.com/${id}?auto=format&fit=crop&w=${w}&q=70`;

export type Stop = {
  id: string;
  time: string;
  category: string;
  name: string;
  desc: string;
  img: string;
  tag?: string;
  rating?: number;
  reviews?: number;
  price: string;
  cost: number;
  status?: { text: string; tone: "mint" | "coral" | "sky" };
  tip?: string;
  action?: string;
  lat: number;
  lon: number;
};
export type Leg = { text: string; mode: "walk" | "transit" | "car" };
export type Day = { n: number; title: string; date: string; area: string; stops: Stop[]; legs: Leg[] };

export const trip = {
  id: "rajasthan-winter",
  folder: "India Trips",
  name: "Rajasthan Winter Loop",
  title: "Jaipur & Udaipur: Forts, Lake Palaces & Royal Thalis",
  dates: "Dec 12 – Dec 16 (5 Days)",
  travelers: 2,
  budget: "Moderate • ₹48,000 total",
  vibe: "Foodie & Heritage",
  city: { name: "Jaipur", lat: 26.9239, lon: 75.8267 },
  cover: u("photo-1477587458883-47145ed94245", 1600),
};

export const days: Day[] = [
  {
    n: 1, title: "Arrival in Jaipur & Pink City Evening", date: "Friday, Dec 12", area: "Old City & Bazaars",
    stops: [
      { id: "s1", time: "02:30 PM", category: "Check-in", name: "Haveli Rani Mahal", desc: "Restored 19th-century haveli with frescoed courtyards and a rooftop café, walking distance to the old city gates.", img: u("photo-1566073771259-6a8506099945"), tag: "Boutique Stay", rating: 4.8, reviews: 512, price: "₹6,200 / night", cost: 6200, status: { text: "Confirmed", tone: "mint" }, lat: 26.9196, lon: 75.8121 },
      { id: "s2", time: "05:30 PM", category: "Cultural walk", name: "Hawa Mahal & Johari Bazaar", desc: "Catch the honeycomb façade at golden hour, then wander jewellers' lanes and textile shops.", img: u("photo-1599661046289-e31897846e41"), tag: "Golden Hour", price: "₹200 entry", cost: 200, status: { text: "Free exploration", tone: "sky" }, tip: "Best photos are from the cafés opposite Hawa Mahal between 5:15 and 6:00 PM.", lat: 26.9239, lon: 75.8267 },
      { id: "s3", time: "08:00 PM", category: "Culinary experience", name: "Dinner at Suvarna Mahal", desc: "Royal Rajasthani thali served in the gilded former banquet hall of Rambagh Palace.", img: u("photo-1585937421612-70a008356fbe"), tag: "Chef's Table", price: "₹₹₹₹ • ₹4,500 / pp", cost: 9000, status: { text: "Action needed", tone: "coral" }, tip: "Reservation needed 7 days ahead. Table request queued for Dec 12, 8:00 PM.", action: "View menu", lat: 26.8981, lon: 75.8077 },
    ],
    legs: [{ text: "12 min auto-rickshaw (3.1 km) to Badi Chaupar", mode: "car" }, { text: "18 min drive (4.6 km) to Rambagh Palace", mode: "car" }],
  },
  {
    n: 2, title: "Amber Fort, Stepwells & Sunset at Nahargarh", date: "Saturday, Dec 13", area: "Amer & Aravalli Hills",
    stops: [
      { id: "s4", time: "08:00 AM", category: "Scenic landmark", name: "Amber Fort", desc: "Arrive at opening to beat the crowds; Sheesh Mahal's mirror work glows in morning light.", img: u("photo-1477587458883-47145ed94245"), tag: "Early Slot", price: "₹500 entry • 2.5 hr", cost: 1000, action: "Route directions", lat: 26.9855, lon: 75.8513 },
      { id: "s5", time: "11:00 AM", category: "Hidden gem", name: "Panna Meena ka Kund", desc: "Symmetrical 16th-century stepwell a short walk from the fort, quiet before noon.", img: u("photo-1590050752117-238cb0fb12b1"), tag: "Local Favourite", rating: 4.6, price: "Free", cost: 0, lat: 26.9876, lon: 75.8551 },
      { id: "s6", time: "01:00 PM", category: "Lunch", name: "1135 AD", desc: "Rajput-style dining inside Amber Fort's palace walls. Try the laal maas.", img: u("photo-1517244683847-7456b63c5969"), tag: "Inside the Fort", rating: 4.5, price: "Moderate • ₹1,800 / pp", cost: 3600, status: { text: "Reservation confirmed", tone: "mint" }, lat: 26.9858, lon: 75.8509 },
      { id: "s7", time: "05:00 PM", category: "Iconic viewpoint", name: "Nahargarh Fort Sunset", desc: "Ramparts overlooking the whole Pink City as the lights come on.", img: u("photo-1603262110263-fb0112e7cc33"), tag: "Must See", price: "₹200 entry • closes 10 PM", cost: 400, action: "Add sunset café", lat: 26.9373, lon: 75.8155 },
    ],
    legs: [{ text: "5 min walk directly to the stepwell", mode: "walk" }, { text: "8 min walk back up to the fort", mode: "walk" }, { text: "Transit: 35 min cab via Amer Road (₹450)", mode: "transit" }],
  },
  {
    n: 3, title: "Train to Udaipur & Lake Pichola", date: "Sunday, Dec 14", area: "Udaipur Old City",
    stops: [
      { id: "s8", time: "06:00 AM", category: "Transit", name: "Jaipur → Udaipur Intercity", desc: "Scenic 7-hour rail journey through Ajmer and the Aravallis.", img: u("photo-1474487548417-781cb71495f3"), price: "₹1,450 / pp", cost: 2900, status: { text: "Booked", tone: "mint" }, lat: 26.9196, lon: 75.7878 },
      { id: "s9", time: "05:30 PM", category: "Boat ride", name: "Lake Pichola Sunset Cruise", desc: "Glide past City Palace and Jag Mandir as the ghats light up.", img: u("photo-1568495248636-6432b97bd949"), tag: "Golden Hour", rating: 4.9, price: "₹900 / pp", cost: 1800, lat: 24.5764, lon: 73.6835 },
    ],
    legs: [{ text: "20 min cab from Udaipur station to Lal Ghat", mode: "car" }],
  },
];

export const picks = [
  { name: "Anokhi Museum of Hand Printing", kind: "Craft & Textiles", tag: "Hidden Gem", rating: 4.7, price: "₹80 • 45 mins", day: 2, img: u("photo-1528360983277-13d401cdc186") },
  { name: "Blue Pottery Workshop", kind: "Hands-on Class", tag: "Top Rated Craft", rating: 4.9, price: "₹1,500 • 90 mins", day: 1, img: u("photo-1565193566173-7a0ee3dbe261") },
  { name: "Chokhi Dhani Village Night", kind: "Night Event", tag: "Evening Pick", rating: 4.5, price: "₹1,100 • 3 hrs", day: 1, img: u("photo-1514525253161-7a46d19cd819") },
  { name: "Galta Ji Monkey Temple", kind: "Temple & Hike", tag: "Local Favourite", rating: 4.4, price: "Free • 2 hrs", day: 2, img: u("photo-1524492412937-b28074a5d7da") },
];

export const trips = [
  { id: trip.id, name: trip.name, dest: "Jaipur, Udaipur", dates: "Dec 12 – 16", days: 5, status: "Planning", img: trip.cover },
  { id: "goa-ny", name: "Goa New Year", dest: "North & South Goa", dates: "Dec 29 – Jan 2", days: 5, status: "Draft", img: u("photo-1512343879784-a960bf40e7f2") },
  { id: "kerala", name: "Kerala Backwaters", dest: "Kochi, Alleppey, Munnar", dates: "Feb 6 – 12", days: 7, status: "Ready", img: u("photo-1602216056096-3b40cc0c9944") },
];

export const destinations = [
  { name: "Jaipur", country: "Rajasthan", img: u("photo-1477587458883-47145ed94245") },
  { name: "Goa", country: "Goa", img: u("photo-1512343879784-a960bf40e7f2") },
  { name: "Udaipur", country: "Rajasthan", img: u("photo-1568495248636-6432b97bd949") },
  { name: "Kerala", country: "Kerala", img: u("photo-1602216056096-3b40cc0c9944") },
  { name: "Manali", country: "Himachal", img: u("photo-1626621341517-bbf3d9990a23") },
  { name: "Varanasi", country: "Uttar Pradesh", img: u("photo-1561361513-2d000a50f0dc") },
];

export const costs = {
  budget: 48000,
  categories: [
    { name: "Stays", amount: 18600, icon: "hotel", color: "#ff5a36" },
    { name: "Food", amount: 12600, icon: "restaurant", color: "#059669" },
    { name: "Transport", amount: 6650, icon: "train", color: "#0f172a" },
    { name: "Activities", amount: 3600, icon: "local_activity", color: "#6366f1" },
    { name: "Shopping", amount: 2500, icon: "shopping_bag", color: "#f59e0b" },
  ],
};

export const versions = [
  { id: "v6", label: "Swapped Day 2 lunch to 1135 AD", by: "You", when: "Just now", current: true },
  { id: "v5", label: "AI smart reorder of Day 1", by: "TripBook AI", when: "2 hours ago" },
  { id: "v4", label: "Added Lake Pichola cruise", by: "Aarav", when: "Yesterday, 9:14 PM" },
  { id: "v3", label: "Budget changed to Moderate", by: "You", when: "Yesterday, 6:02 PM" },
  { id: "v2", label: "Regenerated Day 3", by: "TripBook AI", when: "Nov 15, 11:40 AM" },
  { id: "v1", label: "First itinerary generated", by: "TripBook AI", when: "Nov 15, 11:31 AM" },
];

export const places = [...days.flatMap((d) => d.stops), ...[]].filter((s) => s.category !== "Transit" && s.category !== "Check-in");

export const user = { name: "Kirtan", initials: "KC", email: "you@example.com", home: "Ahmedabad", style: ["Foodie", "Heritage", "Slow travel"] };

export function inr(n: number) {
  return "₹" + n.toLocaleString("en-IN");
}
