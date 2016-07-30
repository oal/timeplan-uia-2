### UiA Timeplan v2
http://timeplaner.olav.it/

Dette er et verktøy / nettside for å hente ut timeplaner fra Universitetet i Agder. Det kan brukes fra Python med `TimeTableManager`-klassen i `manager.py`, eller via nettsiden over.

### Installasjon / kjøring
Krever Python 3.x, og `lxml` krever `python3-dev` eller tilsvarende.
```
virtualenv env -p python3
. env/bin/activate
pip install -r requirements.txt
python main.py
```

### Lisens
Apache 2.0