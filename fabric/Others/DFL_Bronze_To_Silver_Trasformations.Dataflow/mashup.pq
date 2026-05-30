[StagingDefinition = [Kind = "FastCopy"]]
section Section1;
[DataDestinations = {[Definition = [Kind = "Reference", QueryName = "wind_power_DataDestination", IsNewTarget = true], Settings = [Kind = "Automatic", TypeSettings = [Kind = "Table"]]]}]
shared wind_power = let
  Origine = Lakehouse.Contents(null),
  Navigazione = Origine{[workspaceId = "67f93c7d-b2ea-40e5-9934-a9c7ae08d4a6"]}[Data],
  #"Navigazione 1" = Navigazione{[lakehouseId = "efd78bba-7151-4683-9eac-ffbaba521ff2"]}[Data],
  #"Navigazione 2" = #"Navigazione 1"{[Id = "wind_power", ItemKind = "Table"]}[Data],
  Arrotondato = Table.TransformColumns(#"Navigazione 2", {{"wind_speed", each Number.Round(_, 2), type number}, {"energy_produced", each Number.Round(_, 2), type number}}),
  #"Giorno inserito" = Table.AddColumn(Arrotondato, "Giorno", each Date.Day([date]), type nullable number),
  #"Mese inserito" = Table.AddColumn(#"Giorno inserito", "Mese", each Date.Month([date]), type nullable number),
  #"Trimestre inserito" = Table.AddColumn(#"Mese inserito", "Trimestre", each Date.QuarterOfYear([date]), type nullable number),
  #"Anno inserito" = Table.AddColumn(#"Trimestre inserito", "Anno", each Date.Year([date]), type nullable number),
  #"Tipo di colonna modificato" = Table.TransformColumnTypes(#"Anno inserito", {{"Giorno", Int64.Type}, {"Mese", Int64.Type}, {"Trimestre", Int64.Type}, {"Anno", Int64.Type}}),
  #"Colonne rinominate" = Table.RenameColumns(#"Tipo di colonna modificato", {{"Giorno", "giorno"}, {"Mese", "mese"}, {"Trimestre", "trimestre"}, {"Anno", "anno"}}),
  #"Valore sostituito" = Table.ReplaceValue(#"Colonne rinominate", "-", ":", Replacer.ReplaceText, {"time"}),
  #"Colonna duplicata" = Table.DuplicateColumn(#"Valore sostituito", "time", "time - Copia"),
  #"Dividi colonna in base al delimitatore" = Table.SplitColumn(#"Colonna duplicata", "time - Copia", Splitter.SplitTextByDelimiter(":"), {"time - Copia.1", "time - Copia.2", "time - Copia.3"}),
  #"Tipo di colonna modificato 1" = Table.TransformColumnTypes(#"Dividi colonna in base al delimitatore", {{"time - Copia.1", Int64.Type}, {"time - Copia.2", Int64.Type}, {"time - Copia.3", Int64.Type}}, "it"),
  #"Colonne rinominate 1" = Table.RenameColumns(#"Tipo di colonna modificato 1", {{"time - Copia.1", "ora del giorno"}, {"time - Copia.2", "minuti dell'ora"}, {"time - Copia.3", "secodi dei minuti"}}),
  #"Aggiunta colonna personalizzata" = Table.TransformColumnTypes(Table.AddColumn(#"Colonne rinominate 1", "time_period", each if [ora del giorno] >= 5 and [ora del giorno] < 12 then "mattina"
else if [ora del giorno] >= 12 and [ora del giorno] < 17 then "pomeriggio" 
else if [ora del giorno] >= 17 and [ora del giorno] < 21 then "sera" 
else "notte"), {{"time_period", type text}})
in
  #"Aggiunta colonna personalizzata";
shared wind_power_DataDestination = let
  Pattern = Lakehouse.Contents([CreateNavigationProperties = false, EnableFolding = false, HierarchicalNavigation = true, EnableVorder = true, OutputMetadataRefresh = true]),
  Navigation_1 = Pattern{[workspaceId = "67f93c7d-b2ea-40e5-9934-a9c7ae08d4a6"]}[Data],
  Navigation_2 = Navigation_1{[lakehouseId = "a21dccda-0594-4fa4-a6f0-1fbcb0b02102"]}[Data],
  Navigation_3 = Navigation_2{[Id = "dbo", ItemKind = "Schema"]}[Data],
  TableNavigation = Navigation_3{[Id = "wind_power", ItemKind = "Table"]}?[Data]?
in
  TableNavigation;
