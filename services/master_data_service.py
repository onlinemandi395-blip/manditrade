from __future__ import annotations


class MasterDataService:
    RAW_MATERIAL_CATEGORIES = [
        "Cotton",
        "Yarn",
        "Fabric Inputs",
        "Dyes / Chemicals",
        "Packaging Material",
        "Agri Produce",
        "Metals",
        "Construction Inputs",
        "General Bulk Supply",
    ]
    PRODUCT_CATEGORIES = [
        "Grocery / Kirana",
        "Grains / Rice / Wheat",
        "Pulses / Dal",
        "Spices / Masala",
        "Fruits & Vegetables",
        "Dairy",
        "Bakery",
        "Snacks / Packaged Food",
        "Construction Material",
        "Cement",
        "Steel / Iron",
        "Hardware",
        "Electrical",
        "Plumbing",
        "Paints",
        "Tiles / Sanitary",
        "Textile / Garments",
        "Footwear",
        "Furniture",
        "Electronics",
        "Mobile / Accessories",
        "Agriculture Inputs",
        "Fertilizer / Seeds",
        "Animal Feed",
        "Household Items",
        "Stationery",
        "Medicine / Pharmacy",
        "Transport / Logistics",
        "Labour / Services",
        "Other",
    ]

    INDIAN_STATES_AND_UTS = [
        "Andhra Pradesh",
        "Arunachal Pradesh",
        "Assam",
        "Bihar",
        "Chhattisgarh",
        "Goa",
        "Gujarat",
        "Haryana",
        "Himachal Pradesh",
        "Jharkhand",
        "Karnataka",
        "Kerala",
        "Madhya Pradesh",
        "Maharashtra",
        "Manipur",
        "Meghalaya",
        "Mizoram",
        "Nagaland",
        "Odisha",
        "Punjab",
        "Rajasthan",
        "Sikkim",
        "Tamil Nadu",
        "Telangana",
        "Tripura",
        "Uttar Pradesh",
        "Uttarakhand",
        "West Bengal",
        "Andaman and Nicobar Islands",
        "Chandigarh",
        "Dadra and Nagar Haveli and Daman and Diu",
        "Delhi",
        "Jammu and Kashmir",
        "Ladakh",
        "Lakshadweep",
        "Puducherry",
    ]

    def get_product_categories(self) -> list[str]:
        return list(self.PRODUCT_CATEGORIES)

    def get_indian_states_and_union_territories(self) -> list[str]:
        return list(self.INDIAN_STATES_AND_UTS)

    def get_raw_material_categories(self) -> list[str]:
        return list(self.RAW_MATERIAL_CATEGORIES)
