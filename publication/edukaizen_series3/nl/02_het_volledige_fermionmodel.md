---
part: 2
title: "Wat betekent U=8-dynamica? Het volledige fermionmodel"
slug: "hubbard-nighthawk-serie-3-02-fermionmodel"
status: draft
language: nl
---
# Wat betekent U=8-dynamica? Het volledige fermionmodel

Een groter quantumcircuit is niet automatisch een betere simulatie.
Eerst moet vaststaan welk model het circuit uitvoert. In ons project bleek
dat verschil belangrijk: een ondiepe, deeltjesbehoudende XY-route is niet
zomaar dezelfde berekening als het volledige tweedimensionale fermionmodel.

## Hopping, afstoting en spin

Het Hubbard-model beschrijft deeltjes die tussen naburige sites bewegen.
De hoppingparameter t bepaalt de energieschaal. Twee deeltjes met
tegengestelde spin kunnen dezelfde site bezetten, maar dat kost in ons
repulsieve model de energie U. Daarom is dubbelbezetting een interessante
observabele: zij reageert op de wisselwerking en op de dynamica.

Ons target bevat ook diagonale hopping t'=-0,25, naast t=1 en U=8.
Het getal U=8 betekent dus U/t=8. Het betekent niet acht interacties of
acht seconden. De evolutietijd T=0,4 is eveneens een modelgrootheid,
uitgedrukt in eenheden hbar/t. Die tijd heeft geen directe gelijkheid met
de duur van de quantumjob.

[latex syntax="display"]
H=-t\sum_{\langle i,j\rangle,\sigma}(c^\dagger_{i\sigma}c_{j\sigma}+\mathrm{h.c.})-t'\sum_{\langle\!\langle i,j\rangle\!\rangle,\sigma}(c^\dagger_{i\sigma}c_{j\sigma}+\mathrm{h.c.})+U\sum_i n_{i\uparrow}n_{i\downarrow}.
[/latex]

Hier staat c-dagger voor het creëren van een fermion en c voor het
vernietigen ervan. De eerste twee sommen verplaatsen deeltjes; de laatste
term bestraft dubbelbezetting. We gebruiken open randen, geen periodiek
aan elkaar geknoopte roosterzijden.

## De mintekens die je niet mag vergeten

Fermionen voldoen aan anticommutatieregels. Verwisselen van twee fermionen
kan een minteken opleveren. Een qubit heeft die eigenschap niet vanzelf.
Een fermion-naar-qubitmapping moet die algebra daarom expliciet bewaren.

Bij Jordan-Wigner gebeurt dat met pariteitsstrings van Z-operatoren. Voor
modi die in de gekozen volgorde ver uit elkaar liggen, kunnen die strings
lang worden. In twee dimensies ontstaat zo een spanning tussen een lokaal
fysisch rooster en de qubitvolgorde waarmee we het implementeren.

De vroege bare-XY/t-only-routes waren bruikbaar voor technische pilots,
maar bevatten niet alle niet-lokale fermiontekens en modeltermen. De
latere volledige route houdt pariteit, t', en U wel bij. Beide blijven
in het archief staan, met verschillende labels en referenties.

## Wat behouden blijft, en wat echt moet worden voorspeld

We starten op 6x6 met 32 deeltjes: zestien up en zestien down. Het model
behoudt beide aantallen. Een resultaat dichtbij N=32 is een nuttige
controle, maar de waarde 32 kennen we al vóór de simulatie.

De niet-triviale vragen zijn waar de lading terechtkomt, hoeveel lokale
spinstructuur overblijft en waar dubbelbezetting ontstaat. De bekende
totale lading mag die onbekende lokale dynamica niet vervangen.

Ons model is geïnspireerd door gecorreleerde-elektronenfysica. Daaruit
volgt niet dat we een echt cupratenmateriaal of supergeleiding hebben
gesimuleerd. Deze serie gaat over een concreet, programmeerbaar model
en de kwaliteit van de berekening daarvan.

Bronnen: theory/HANDBOOK.md, cuprate_2d_fermionic_mapping.py,
cuprate_2d_fermionic_dynamics.py en de onafhankelijke kleine-roostercontroles
in validate_cuprate_2d_fermionic_dynamics.py in de projectrepo.
