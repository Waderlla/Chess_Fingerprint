from data_fetcher import main

# Uruchamia miesięczny sync danych źródłowych:
# - pobiera brakujące partie
# - nie zapisuje duplikatów
# - czyści stare partie poza oknem retencji
main()
