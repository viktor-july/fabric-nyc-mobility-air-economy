[StagingDefinition = [Kind = "FastCopy"]]
section Section1;
[DataDestinations = {[Definition = [Kind = "Reference", QueryName = "Bronze_FX_DataDestination", IsNewTarget = true], Settings = [Kind = "Automatic", TypeSettings = [Kind = "Table"]]]}]
shared Bronze_FX = let
  Source = Csv.Document(Web.Contents("https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?format=csvdata"), [Delimiter = ",", Columns = 32, QuoteStyle = QuoteStyle.None]),
  #"Promoted headers" = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
  #"Changed column type" = Table.TransformColumnTypes(#"Promoted headers", {{"KEY", type text}, {"FREQ", type text}, {"CURRENCY", type text}, {"CURRENCY_DENOM", type text}, {"EXR_TYPE", type text}, {"EXR_SUFFIX", type text}, {"TIME_PERIOD", type date}, {"OBS_VALUE", type number}, {"OBS_STATUS", type text}, {"OBS_CONF", type text}, {"OBS_PRE_BREAK", type text}, {"OBS_COM", type text}, {"TIME_FORMAT", type duration}, {"BREAKS", type text}, {"COLLECTION", type text}, {"COMPILING_ORG", type text}, {"DISS_ORG", type text}, {"DOM_SER_IDS", type text}, {"PUBL_ECB", type text}, {"PUBL_MU", type text}, {"PUBL_PUBLIC", type text}, {"UNIT_INDEX_BASE", type text}, {"COMPILATION", type text}, {"COVERAGE", type text}, {"DECIMALS", Int64.Type}, {"NAT_TITLE", type text}, {"SOURCE_AGENCY", type text}, {"SOURCE_PUB", type text}, {"TITLE", type text}, {"TITLE_COMPL", type text}, {"UNIT", type text}, {"UNIT_MULT", Int64.Type}}),
  #"Removed columns" = Table.RemoveColumns(#"Changed column type", {"FREQ", "EXR_TYPE", "EXR_SUFFIX", "UNIT_MULT", "UNIT", "TITLE_COMPL", "TITLE", "SOURCE_PUB", "SOURCE_AGENCY", "NAT_TITLE", "DECIMALS", "COVERAGE", "COMPILATION", "UNIT_INDEX_BASE", "PUBL_PUBLIC", "PUBL_MU", "PUBL_ECB", "DOM_SER_IDS", "DISS_ORG", "COMPILING_ORG", "COLLECTION", "BREAKS", "TIME_FORMAT", "OBS_COM", "OBS_PRE_BREAK", "OBS_CONF", "OBS_STATUS"})
in
  #"Removed columns";
[DataDestinations = {[Definition = [Kind = "Reference", QueryName = "US_GDP_DataDestination", IsNewTarget = true], Settings = [Kind = "Automatic", TypeSettings = [Kind = "Table"]]]}]
shared US_GDP = let
  Source = Json.Document(Web.Contents("https://api.worldbank.org/v2/country/USA/indicator/NY.GDP.MKTP.CD?format=json&per_page=100")),
  #"Converted to table" = Table.FromList(Source, Splitter.SplitByNothing(), null, null, ExtraValues.Error),
  Navigation = #"Converted to table"{1}[Column1],
  #"Converted to table 1" = Table.FromList(Navigation, Splitter.SplitByNothing(), null, null, ExtraValues.Error),
  #"Expanded Column1" = Table.ExpandRecordColumn(#"Converted to table 1", "Column1", {"indicator", "country", "countryiso3code", "date", "value", "unit", "obs_status", "decimal"}, {"indicator", "country", "countryiso3code", "date", "value", "unit", "obs_status", "decimal"}),
  #"Expanded indicator" = Table.ExpandRecordColumn(#"Expanded Column1", "indicator", {"id", "value"}, {"indicator.id", "indicator.value"}),
  #"Expanded country" = Table.ExpandRecordColumn(#"Expanded indicator", "country", {"id", "value"}, {"country.id", "country.value"}),
  #"Removed columns" = Table.RemoveColumns(#"Expanded country", {"obs_status", "unit"}),
  #"Changed column type" = Table.TransformColumnTypes(#"Removed columns", {{"indicator.id", type text}, {"date", type date}, {"value", Int64.Type}, {"decimal", type number}, {"country.id", type text}, {"indicator.value", type text}, {"country.value", type text}, {"countryiso3code", type text}})
in
  #"Changed column type";
shared NavigationQuery = let
  Source = Lakehouse.Contents([HierarchicalNavigation = true, EnableVorder = true, OutputMetadataRefresh = true, CreateNavigationProperties = false, EnableFolding = false])
in
  Source;
shared Bronze_FX_DataDestination = let
  Pattern = Lakehouse.Contents([HierarchicalNavigation = true, EnableVorder = true, OutputMetadataRefresh = true, CreateNavigationProperties = false, EnableFolding = false]),
  Navigation_1 = Pattern{[workspaceId = "ddd76090-4451-4a74-80b1-5e6c6747ef20"]}[Data],
  Navigation_2 = Navigation_1{[lakehouseId = "175b3837-9b91-4dde-b912-ced02782891b"]}[Data],
  Navigation_3 = Navigation_2{[Id = "dbo", ItemKind = "Schema"]}[Data],
  TableNavigation = Navigation_3{[Id = "Bronze_ECB_FX", ItemKind = "Table"]}?[Data]?
in
  TableNavigation;
shared US_GDP_DataDestination = let
  Pattern = Lakehouse.Contents([HierarchicalNavigation = true, EnableVorder = true, OutputMetadataRefresh = true, CreateNavigationProperties = false, EnableFolding = false]),
  Navigation_1 = Pattern{[workspaceId = "ddd76090-4451-4a74-80b1-5e6c6747ef20"]}[Data],
  Navigation_2 = Navigation_1{[lakehouseId = "175b3837-9b91-4dde-b912-ced02782891b"]}[Data],
  Navigation_3 = Navigation_2{[Id = "dbo", ItemKind = "Schema"]}[Data],
  TableNavigation = Navigation_3{[Id = "Bronze_WorldBank_GDP", ItemKind = "Table"]}?[Data]?
in
  TableNavigation;
