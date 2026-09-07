# Theoriehandboek: 2D Fermi-Hubbard op Nighthawk

Dit handboek bundelt de theorie achter het project. De originele protocollen,
implementaties en controles blijven daarnaast integraal bewaard. Het is geen
claim dat alle besproken mappings of mitigatiemethoden in de laatste run zijn
gebruikt. Conventies hieronder gelden voor het volledige fermionmodel.

## 1. Van rooster naar Hamiltoniaan

Een site heeft twee fermionmodi: spin omhoog en spin omlaag. Daardoor zijn
de vier lokale bezettingen leeg, up, down en dubbelbezet mogelijk. Een 6x6
rooster telt 36 sites en 72 modi; in de gebruikte directe encoding zijn dat
72 qubits. Dat betekent niet 72 deeltjes: onze begintoestand heeft N=32.

Met hbar=1 gebruiken we

\[
H=-t\sum_{\langle i,j\rangle,\sigma}(c^\dagger_{i\sigma}c_{j\sigma}+\mathrm{h.c.})
-t'\sum_{\langle\!\langle i,j\rangle\!\rangle,\sigma}(c^\dagger_{i\sigma}c_{j\sigma}+\mathrm{h.c.})
+U\sum_i n_{i\uparrow}n_{i\downarrow}-\mu\sum_{i,\sigma}n_{i\sigma}.
\]

Onze target gebruikt t=1, t'=-0.25, U=8 en open randen. T=0.4 betekent
een dimensieloze evolutietijd in eenheden hbar/t, niet 0.4 seconde op hardware.
Een uniforme chemische potentiaal levert in een vaste-N-sector slechts een
globale fase op. Dat maakt het getal N niet tot een onafhankelijke dynamische
voorspelling: [H,N]=0 en ook N_up en N_down worden behouden.

De vier gaten zijn gedefinieerd ten opzichte van een enkelbezette 36-site
achtergrond. Dat geeft N=32 en gatendoping 4/36. Een ander gatpatroon of
een andere t' is een andere opgave, ook als roostermaat en U overeenkomen.
Het model is cupraten-geinspireerd; deze simulatie bewijst geen materiaalgedrag,
d-wave orde of supergeleiding.

## 2. Fermiontekens zijn onderdeel van de fysica

De operatoren voldoen aan {c_p,c_q^dagger}=delta_pq en {c_p,c_q}=0.
Met de bezettingsconventie n=(I-Z)/2 is de Jordan-Wigner-afbeelding

\[
c_p=\left(\prod_{q<p} Z_q\right)(X_p+iY_p)/2.
\]

De pariteitsstring bewaart het minteken bij verwisseling van fermionen.
Alleen een XY-term tussen ver uit elkaar liggende qubits gebruiken verwijdert
die string en is in het algemeen niet hetzelfde 2D Hubbard-model. In de
historische number_preserving-families was dit een expliciete beperking.
De bestanden blijven reproduceerbaar, maar gelden niet als validatie van de
latere volledige fermionroute.

Een fSWAP verwisselt bezettingen en geeft |11> een extra minteken. Mapping
gaat daarom over algebra, beginbezetting, observabelen EN fysieke routing.
Een gunstige logische Pauli-lengte garandeert geen gunstig native circuit.

## 3. Dynamica en twee verschillende benaderingsfouten

De exacte toestand is exp(-iHT)|psi(0)>. De uitgevoerde route benadert deze
evolutie met een symmetrische productformule. Voor een tweedeling H=A+B is
een stap exp(-iA dt/2) exp(-iB dt) exp(-iA dt/2). Meer termgroepen geven
een overeenkomstige symmetrische volgorde. Voor begrensde termen is de
gebruikelijke globale asymptotische foutorde O(T dt^2), met constanten die
van commutatoren afhangen. Die orde levert niet vanzelf een numerieke
foutgrens voor ons grote rooster op.

Bij het huidige target is T=0.4 met twee stappen van dt=0.2. Een MPS die
precies dat circuit nabootst kan de circuitimplementatie toetsen. Hij
certificeert daarmee nog niet de continue Hamiltoniaandynamica. Zowel
tijdstapverfijning als bond-dimensieverfijning moet afzonderlijk gebeuren.

qDRIFT bemonstert Hamiltoniaantermen in plaats van alle termen systematisch
te doorlopen. Het is een andere benadering met eigen fout- en samplebudget.
Ancilla-encodings en Bonsai veranderen de representatie en routing. Geen
van deze ideeen mag als gerealiseerde hardwarewinst worden gerapporteerd
zonder een gecompileerde vergelijking en controle van dezelfde fysica.

## 4. Lading, spin en doublons

De drie lokale observabelen zijn C_i=<n_up+n_down>, S_i=<n_up-n_down>
en D_i=<n_up n_down>. Onze spin is tweemaal de conventionele fysieke S_z.
Google gebruikt in Eq. B1 van arXiv:2510.26845v2 reeds dezelfde n_up-n_down:
bij onze omrekening is dus geen extra factor twee toegepast.

Uit gemeten Pauli-momenten volgt

\[
C_i=1-(\langle Z_\uparrow\rangle+\langle Z_\downarrow\rangle)/2,
\quad S_i=(\langle Z_\downarrow\rangle-\langle Z_\uparrow\rangle)/2,
\]
\[
D_i=(1-\langle Z_\uparrow\rangle-\langle Z_\downarrow\rangle+
\langle Z_\uparrow Z_\downarrow\rangle)/4.
\]

N=sum_i C_i; het gemiddelde D is sum_i D_i/L. Spinprofiel-RMS is
sqrt(sum_i S_i^2/L), terwijl RMS-afwijking de wortel uit het gemiddelde
van (S_i-S_i_ref)^2 is. Een gemiddeld doublongetal kan goed lijken terwijl
positieve en negatieve lokale fouten elkaar opheffen.

De vier gereconstrueerde kansen zijn P11=D, P10=(C+S)/2-D,
P01=(C-S)/2-D en P00=1-C+D. Negatieve waarden na mitigatie zijn een
waarschuwing; we knippen ze niet stilzwijgend af. Een exact modelconstraint
N=32 naast een tabel vermelden is correct. Het gemeten N vervangen door 32
en dit als hardwarevalidatie voorstellen is dat niet.

## 5. Mitigatie: verschillende doelen

Readout-mitigatie corrigeert een geschatte verwarringsmatrix van de meting.
Zij herstelt niet automatisch fouten die tijdens de poorten zijn ontstaan.
Onze lokale readoutmethode en haar aannames staan in de analysescripts;
correlaties tussen meetfouten kunnen buiten dat model vallen.

ZNE schat een nul-ruislimiet uit circuits met verhoogde ruis. CZ-folding
vervangt bijvoorbeeld CZ door drie CZ's, logisch dezelfde poort, mits de
compiler die extra poorten niet weer verwijdert. Extrapolatie kost shots en
kan variantie versterken. PEC gebruikt getekende quasi-kansgewichten op
basis van een ruismodel en kan een grote sample-overhead veroorzaken.
DD onderdrukt bepaalde verstoringen tijdens geschikte wachttijden; het is
geen algemene foutcorrectie en was uitgeschakeld in de laatste gepaarde run.

TFLO leert een correctie met circuits die klassiek efficient oplosbaar zijn
via fermionische lineaire optica. Hier zijn U=0-circuits de training; de
interagerende U=8-target is niet als juiste uitkomst aan de fit gegeven.
Een holdout is een niet-gebruikte, wel exact bekende controle. Een aanvullende
ablatie verwijdert targethardware-input om te testen hoeveel de training zelf
al verklaart. In onze laatste run slaagden de holdouts niet en was de ablatie
op sommige metrics dichter bij chi64. Dat begrenst de interpretatie van TFLO.

## 6. Klassieke kosten en ons snelheidsdoel

Een volledige toestandsvector groeit exponentieel in het aantal modi. Een
MPS bewaart daarentegen een gecomprimeerde toestand met bond-dimensie chi.
De bruikbaarheid hangt af van de verstrengeling en de gevraagde observabelen.
Een groter rooster maakt klassiek rekenen niet op iedere korte tijd en voor
iedere observabele automatisch onhaalbaar. Niet-interagerende U=0-dynamica
is bovendien een aparte, efficient klassieke referentieroute.

Onze gemeten chi64-kernelduur is 150.819 s. Delen door 8 s of 7 s QPU-usage
geeft 18.85 of 21.55. Dit is de concrete ~20x mijlpaal. De noemer is geen
totale doorlooptijd en chi64 is geen gecertificeerde gelijke-nauwkeurigheid
baseline. Import, wachtrij, kalibraties, mitigatietraining en analyse moeten
in een toekomstige end-to-end vergelijking expliciet worden geboekt.

## 7. Bronnen en bewaarde verdieping

- [Google/Phasecraft, 72-qubit dynamica](https://arxiv.org/abs/2510.26845v2)
- [Bijbehorende numerieke data](https://zenodo.org/records/17881822)
- [TFLO, Montanaro en Stanisic](https://arxiv.org/abs/2102.02120)
- [ZNE en PEC, Temme, Bravyi en Gambetta](https://arxiv.org/abs/1612.02058)
- [Bonsai-mapping](https://arxiv.org/abs/2212.09731)
- [Heavy-hex Hubbard/Bonsai/qDRIFT](https://arxiv.org/abs/2608.25024)
- [IBM workload usage](https://quantum.cloud.ibm.com/docs/en/guides/estimate-job-run-time)

De theorie in dit handboek is gekoppeld aan de projectprotocollen, niet aan
een voorspelde quantumdoorbraak. Zie EXPERIMENT_INDEX.md voor de concrete
implementaties en hun gecontroleerde of nog openstaande validatiestatus.
