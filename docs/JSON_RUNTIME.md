# JSON Runtime

Runtime flow:

1. Load all JSON config files into Streamlit session cache
2. Resolve role and language
3. Resolve navigation from `navigation.json`
4. Resolve module from `modules.json`
5. Resolve data source from `database.json`
6. Render page dynamically

Repeated file reads are avoided after cache load.
