"""Yellow Pages–style category labels (add lines to extend the catalog)."""

_CATEGORY_LINES = """
Restaurants
Food Delivery
Catering Services
Coffee Shops
Bakeries
Bars
Night Clubs
Hotels
Motels
Bed and Breakfasts
Travel Agencies
Auto Repair
Auto Body Shops
Towing
Car Dealers
Used Car Dealers
Tire Dealers
Oil Change
Auto Parts
Car Wash
Motorcycle Dealers
Truck Repair
Electricians
Plumbers
HVAC Contractors
Roofing Contractors
General Contractors
Home Builders
Painting Contractors
Flooring Contractors
Landscaping
Lawn Care
Tree Services
Handyman Services
Pest Control
Locksmiths
Security Systems
Appliances Repair
Furniture Stores
Home Improvement
Hardware Stores
Moving Companies
Storage
Cleaning Services
Carpet Cleaning
Window Cleaning
Dry Cleaners
Laundromats
Real Estate Agents
Property Management
Apartments
Mortgage Lenders
Insurance Agents
Banks
Credit Unions
Accountants
Tax Return Preparation
Attorneys
Dentists
Physicians
Chiropractors
Veterinarians
Pharmacies
Optometrists
Hospitals
Medical Clinics
Physical Therapists
Gyms
Yoga Studios
Personal Trainers
Beauty Salons
Barber Shops
Nail Salons
Spas
Tattoo Shops
Florists
Gift Shops
Jewelry Stores
Clothing Stores
Shoe Stores
Electronics Stores
Computer Repair
IT Services
Internet Service Providers
Cell Phone Stores
Photographers
Wedding Services
Event Planning
Printing Services
Signs
Marketing Agencies
Advertising Agencies
Employment Agencies
Staffing Agencies
Office Supplies
Courier Services
Shipping Centers
Post Offices
Day Care
Preschools
Schools
Colleges
Libraries
Churches
Nonprofit Organizations
Pet Grooming
Pet Stores
Animal Shelters
Funeral Homes
Cemeteries
Gas Stations
Convenience Stores
Grocery Stores
Supermarkets
Farmers Markets
Liquor Stores
Wholesale Clubs
Department Stores
Discount Stores
Thrift Stores
Book Stores
Toy Stores
Sporting Goods
Bicycle Shops
Boat Dealers
Marinas
Fishing Charters
Campgrounds
RV Parks
Airports
Taxi Services
Limousine Service
Bus Lines
Trucking Companies
Freight Forwarding
Warehouses
Manufacturing
Machine Shops
Welding
Metal Fabricators
Printing
Packaging
Recycling Centers
Junk Removal
Demolition Contractors
Excavating Contractors
Paving Contractors
Concrete Contractors
Fence Contractors
Swimming Pool Contractors
Solar Energy Equipment
Well Drilling
Surveyors
Architects
Interior Designers
Engineers
Environmental Services
Consultants
Business Brokers
Financial Advisors
Investment Services
Tax Services
Bookkeeping
Payroll Services
Notaries
Translation Services
Driving Schools
Music Lessons
Dance Studios
Art Schools
Theaters
Museums
Bowling Alleys
Golf Courses
Sports Clubs
Marinas
Boat Repair
Aircraft Dealers
Industrial Equipment
Restaurant Equipment
Medical Equipment
Office Equipment Rental
Party Rentals
Equipment Rental
Tool Rental
Scaffolding
Crane Services
Septic Tanks
Water Treatment
Irrigation Systems
Sprinkler Systems
Glass Repair
Screen Repair
Shoe Repair
Tailors
Alterations
Uniforms
Medical Supplies
Home Health Care
Senior Services
Hospice
Child Care
Nanny Services
House Sitting
Pet Sitting
Dog Walkers
Computer Software
Web Design
Digital Marketing
Social Media Marketing
SEO Services
Video Production
Audio Visual Equipment
DJs
Musicians
Bands
Restaurants Italian
Restaurants Mexican
Restaurants Chinese
Restaurants Japanese
Restaurants Indian
Restaurants Thai
Restaurants Pizza
Fast Food Restaurants
Steak Houses
Seafood Restaurants
Vegetarian Restaurants
Vegan Restaurants
Food Trucks
Wineries
Breweries
Distilleries
Distillers
"""


def category_names():
    names = [line.strip() for line in _CATEGORY_LINES.splitlines() if line.strip()]
    return sorted(set(names))
