# Pipeline v2 2026-09-25

## ALARMS

- ACHR: short_history (a big company: fix or add to data/v2/predecessors.csv)
- MRP: short_history (a big company: fix or add to data/v2/predecessors.csv)
- PCT: short_history (a big company: fix or add to data/v2/predecessors.csv)
- big companies with no revenue (64; funds / pre-revenue are expected, anything you recognise as an operating company is a drop): ADAM, APA, APGE, ARCC, ARR, ARXS, AVBP, BANR, BBDC, BHVN, BTGO, BXSL, CBRS, CGBD, CIM, CLBK, CSQR, DX, DYN, ELVN, EWTX, FETH, FRBT, FSK, GBDC, GMRS, GPCR, GSBD, HONA, HTGC, IMVT, INIO, IRON, MAIN, MAIR, MBGL, MC, MLTX, MSDL, NLY, NMFC, NREF, NUVL, OBDC, OCSL, OCTV, OKLO, ORC, ORIC, OTF, PCVX, PFLT, PPTA, PSEC, QS, SLRC, SPCX, TMC, TRIN, TSLX, TWOD, VEL, VERA, VGNT
- big companies reporting in another currency (not read): CP (CAD), ENB (CAD)
- debt_too_small_for_interest: 28 companies (interest is over 25% of the debt v2 found): GE, TMUS, ED, BAX, ALLY, SF, CRBG, KNX, QVCG, CDE, AN, ORA, FRHC, AVA, CACC, SNEX, VAL, NAVN, CALY, CIM, PFLT, COLL, PMT, QURE, GOLD, TRLV, KODK, RDNW
- interest_but_no_debt: 30 companies pay interest but v2 found no debt: BRK-B, KKR, PCAR, ALNY, F, TXT, CG, NLY, TEM, CUBE, AES, AHR, COLD, CNK, HIW, ALH, UE, BANR, PCT, DX, PLUG, ARWR, ARI, HPP, KW, OPY, KREF, OPEN, ARES, TTEC

- run: 250 min
- universe: 2489 companies that could be S&P-sized (no prices: fmp draws the $22.7B line with Robinhood's); by size gate: assets 121, float 1860, no_float 334, revenue 174
- cover instances: 18 fetched of 4782 needed (the rest from the cache); 0 dropped from the cache
- dropped before the universe: commodity_trust 92, no_listed_common_ticker 784, no_recent_10q 165, partnership 40, too_small_sec_figures 1938
- TTM coverage: revenue 2129/2489, net_income 2235/2489, operating_cash_flow 2216/2489, capex 2062/2489, stock_comp 2126/2489, shares_diluted 2302/2489; total_debt 1903/2489
- changes this run: fact_change 127, new_filing 95

## Filing library

- release assets: https://github.com/loosygoosie/sec-dataset/releases/tag/library (one <cik>.tar.gz per company + index.json)
- window: filings since 2023-09-25 (3 years), every form, every document
- this run: 548 companies checked, 119 assets replaced, 64 unchanged; 30746 filings fetched (95 logged as new), 122406 deferred to the next run; 241 min
- library: 548 companies, 177 complete; EDGAR lists 204498 filings, saved 81951 (120449 documents, 1.00 GB); failures 141

### Companies with gaps (EDGAR count != saved)

| ticker | cik | EDGAR | saved | failures | deferred | error |
|---|---|---|---|---|---|---|
| EOG | 821189 | 377 | 363 | 14 | 0 |  |
| STX | 1137789 | 546 | 508 | 38 | 0 |  |
| FDX | 1048911 | 259 | 232 | 27 | 0 |  |
| ADSK | 769397 | 252 | 241 | 11 | 0 |  |
| BNY | 1390777 | 502 | 461 | 41 | 0 |  |
| MRVL | 1835632 | 414 | 188 | 10 | 216 |  |
| NEM | 1164727 | 344 | 0 | 0 | 344 |  |
| CMG | 1058090 | 293 | 0 | 0 | 293 |  |
| ORLY | 898173 | 364 | 0 | 0 | 364 |  |
| HCA | 860730 | 271 | 0 | 0 | 271 |  |
| AXON | 1069183 | 393 | 0 | 0 | 393 |  |
| FCX | 831259 | 196 | 0 | 0 | 196 |  |
| CRH | 849395 | 171 | 0 | 0 | 171 |  |
| HLT | 1585689 | 255 | 0 | 0 | 255 |  |
| EMR | 32604 | 229 | 0 | 0 | 229 |  |
| MAR | 1048286 | 338 | 0 | 0 | 338 |  |
| MSI | 68505 | 330 | 0 | 0 | 330 |  |
| CSX | 277948 | 210 | 0 | 0 | 210 |  |
| ROP | 882835 | 190 | 0 | 0 | 190 |  |
| TRV | 86312 | 466 | 0 | 0 | 466 |  |
| SNPS | 883241 | 308 | 0 | 0 | 308 |  |
| DLR | 1297996 | 227 | 0 | 0 | 227 |  |
| CARR | 1783180 | 225 | 0 | 0 | 225 |  |
| APO | 1858681 | 415 | 0 | 0 | 415 |  |
| AZO | 866787 | 337 | 0 | 0 | 337 |  |
| NSC | 702165 | 590 | 0 | 0 | 590 |  |
| KMI | 1506307 | 243 | 0 | 0 | 243 |  |
| FTNT | 1262039 | 379 | 0 | 0 | 379 |  |
| MNST | 865752 | 240 | 0 | 0 | 240 |  |
| ABNB | 1559720 | 868 | 0 | 0 | 868 |  |
| AEP | 4904 | 404 | 0 | 0 | 404 |  |
| AFL | 4977 | 363 | 0 | 0 | 363 |  |
| PWR | 1050915 | 228 | 0 | 0 | 228 |  |
| TFC | 92230 | 443 | 0 | 0 | 443 |  |
| REGN | 872589 | 327 | 0 | 0 | 327 |  |
| NXPI | 1413447 | 254 | 0 | 0 | 254 |  |
| LNG | 3570 | 182 | 0 | 0 | 182 |  |
| MET | 1099219 | 498 | 0 | 0 | 498 |  |
| ALL | 899051 | 370 | 0 | 0 | 370 |  |
| O | 726728 | 263 | 0 | 0 | 263 |  |
| JCI | 833444 | 391 | 0 | 0 | 391 |  |
| SPG | 1063761 | 345 | 0 | 0 | 345 |  |
| CPRT | 900075 | 147 | 0 | 0 | 147 |  |
| OKE | 1039684 | 456 | 0 | 0 | 456 |  |
| MPC | 1510295 | 265 | 0 | 0 | 265 |  |
| CTVA | 1755672 | 246 | 0 | 0 | 246 |  |
| FLUT | 1635327 | 374 | 0 | 0 | 374 |  |
| AMP | 820027 | 541 | 0 | 0 | 541 |  |
| WDAY | 1327811 | 520 | 0 | 0 | 520 |  |
| SRE | 1032208 | 423 | 0 | 0 | 423 |  |
| PCAR | 75362 | 601 | 0 | 0 | 601 |  |
| EA | 712515 | 465 | 0 | 0 | 465 |  |
| VRT | 1674101 | 379 | 0 | 0 | 379 |  |
| D | 715957 | 299 | 0 | 0 | 299 |  |
| PSX | 1534701 | 382 | 0 | 0 | 382 |  |
| CAH | 721371 | 233 | 0 | 0 | 233 |  |
| WCN | 1318220 | 286 | 0 | 0 | 286 |  |
| FAST | 815556 | 256 | 0 | 0 | 256 |  |
| AIG | 5272 | 463 | 0 | 0 | 463 |  |
| WDC | 106040 | 503 | 0 | 0 | 503 |  |
| TTWO | 946581 | 339 | 0 | 0 | 339 |  |
| GM | 1467858 | 272 | 0 | 0 | 272 |  |
| KR | 56873 | 372 | 0 | 0 | 372 |  |
| LHX | 202058 | 322 | 0 | 0 | 322 |  |
| EW | 1099800 | 387 | 0 | 0 | 387 |  |
| SLB | 87347 | 391 | 0 | 0 | 391 |  |
| TGT | 27419 | 232 | 0 | 0 | 232 |  |
| CMI | 26172 | 377 | 0 | 0 | 377 |  |
| GLW | 24741 | 611 | 0 | 0 | 611 |  |
| KDP | 1418135 | 304 | 0 | 0 | 304 |  |
| CCI | 1051470 | 313 | 0 | 0 | 313 |  |
| PSA | 1393311 | 307 | 0 | 0 | 307 |  |
| EXC | 1109357 | 214 | 0 | 0 | 214 |  |
| CVNA | 1690820 | 926 | 0 | 0 | 926 |  |
| ROST | 745732 | 221 | 0 | 0 | 221 |  |
| MSCI | 1408198 | 215 | 0 | 0 | 215 |  |
| DDOG | 1561550 | 873 | 0 | 0 | 873 |  |
| IDXX | 874716 | 224 | 0 | 0 | 224 |  |
| FERG | 2011641 | 220 | 0 | 0 | 220 |  |
| KMB | 55785 | 298 | 0 | 0 | 298 |  |
| URI | 1067701 | 235 | 0 | 0 | 235 |  |
| ALNY | 1178670 | 262 | 0 | 0 | 262 |  |
| VEEV | 1393052 | 365 | 0 | 0 | 365 |  |
| VRSK | 1442145 | 323 | 0 | 0 | 323 |  |
| FIS | 1136893 | 204 | 0 | 0 | 204 |  |
| F | 37996 | 373 | 0 | 0 | 373 |  |
| TEL | 1385157 | 271 | 0 | 0 | 271 |  |
| PEG | 788784 | 276 | 0 | 0 | 276 |  |
| AME | 1037868 | 237 | 0 | 0 | 237 |  |
| VLO | 1035002 | 180 | 0 | 0 | 180 |  |
| CBRE | 1138118 | 288 | 0 | 0 | 288 |  |
| OXY | 797468 | 197 | 0 | 0 | 197 |  |
| GWW | 277135 | 309 | 0 | 0 | 309 |  |
| YUM | 1041061 | 360 | 0 | 0 | 360 |  |
| NDAQ | 1120193 | 318 | 0 | 0 | 318 |  |
| SNDK | 2023554 | 209 | 0 | 0 | 209 |  |
| XEL | 72903 | 281 | 0 | 0 | 281 |  |
| KVUE | 1944048 | 357 | 0 | 0 | 357 |  |
| CRWV | 1769628 | 1084 | 0 | 0 | 1084 |  |
| XYZ | 1512673 | 637 | 0 | 0 | 637 |  |
| DELL | 1571996 | 1023 | 0 | 0 | 1023 |  |
| DHI | 882184 | 322 | 0 | 0 | 322 |  |
| OTIS | 1781335 | 230 | 0 | 0 | 230 |  |
| CTSH | 1058290 | 620 | 0 | 0 | 620 |  |
| COR | 1140859 | 423 | 0 | 0 | 423 |  |
| PRU | 1137774 | 489 | 0 | 0 | 489 |  |
| BKR | 1701605 | 289 | 0 | 0 | 289 |  |
| CRCL | 1876042 | 364 | 0 | 0 | 364 |  |
| PCG | 1004980 | 248 | 0 | 0 | 248 |  |
| ETR | 65984 | 530 | 0 | 0 | 530 |  |
| CHTR | 1091667 | 359 | 0 | 0 | 359 |  |
| TRGP | 1389170 | 298 | 0 | 0 | 298 |  |
| ED | 1047862 | 261 | 0 | 0 | 261 |  |
| FICO | 814547 | 263 | 0 | 0 | 263 |  |
| HIG | 874766 | 295 | 0 | 0 | 295 |  |
| PAYX | 723531 | 285 | 0 | 0 | 285 |  |
| NET | 1477333 | 620 | 0 | 0 | 620 |  |
| SYY | 96021 | 372 | 0 | 0 | 372 |  |
| RMD | 943819 | 351 | 0 | 0 | 351 |  |
| EQT | 33213 | 359 | 0 | 0 | 359 |  |
| COHR | 820318 | 358 | 0 | 0 | 358 |  |
| VMC | 1396009 | 299 | 0 | 0 | 299 |  |
| VICI | 1705696 | 188 | 0 | 0 | 188 |  |
| GRMN | 1121788 | 346 | 0 | 0 | 346 |  |
| DXCM | 1093557 | 330 | 0 | 0 | 330 |  |
| EBAY | 1065088 | 532 | 0 | 0 | 532 |  |
| MCHP | 827054 | 358 | 0 | 0 | 358 |  |
| GEHC | 1932393 | 268 | 0 | 0 | 268 |  |
| CSGP | 1057352 | 236 | 0 | 0 | 236 |  |
| CPNG | 1834584 | 237 | 0 | 0 | 237 |  |
| WEC | 783325 | 332 | 0 | 0 | 332 |  |
| ACGL | 947484 | 225 | 0 | 0 | 225 |  |
| IR | 1699150 | 293 | 0 | 0 | 293 |  |
| EFX | 33185 | 291 | 0 | 0 | 291 |  |
| DAL | 27904 | 327 | 0 | 0 | 327 |  |
| FWONA | 1560385 | 395 | 0 | 0 | 395 |  |
| TTD | 1671933 | 292 | 0 | 0 | 292 |  |
| BRO | 79282 | 198 | 0 | 0 | 198 |  |
| NUE | 73309 | 295 | 0 | 0 | 295 |  |
| WAB | 943452 | 397 | 0 | 0 | 397 |  |
| XYL | 1524472 | 210 | 0 | 0 | 210 |  |
| EXR | 1289490 | 226 | 0 | 0 | 226 |  |
| ODFL | 878927 | 249 | 0 | 0 | 249 |  |
| STT | 93751 | 1764 | 0 | 0 | 1764 |  |
| IT | 749251 | 644 | 0 | 0 | 644 |  |
| CRDO | 1807794 | 617 | 0 | 0 | 617 |  |
| WTW | 1140536 | 544 | 0 | 0 | 544 |  |
| LPLA | 1397911 | 323 | 0 | 0 | 323 |  |
| IRM | 1020569 | 432 | 0 | 0 | 432 |  |
| MTB | 36270 | 412 | 0 | 0 | 412 |  |
| HUM | 49071 | 248 | 0 | 0 | 248 |  |
| ROK | 1024478 | 514 | 0 | 0 | 514 |  |
| MLM | 916076 | 235 | 0 | 0 | 235 |  |
| VTR | 740260 | 462 | 0 | 0 | 462 |  |
| HEI | 46619 | 173 | 0 | 0 | 173 |  |
| HUBS | 1404655 | 422 | 0 | 0 | 422 |  |
| RJF | 720005 | 372 | 0 | 0 | 372 |  |
| WBD | 1437107 | 484 | 0 | 0 | 484 |  |
| TEAM | 1650372 | 1666 | 0 | 0 | 1666 |  |
| AMRZ | 2035989 | 127 | 0 | 0 | 127 |  |
| DTE | 936340 | 293 | 0 | 0 | 293 |  |
| CNC | 1071739 | 282 | 0 | 0 | 282 |  |
| NRG | 1013871 | 407 | 0 | 0 | 407 |  |
| A | 1090872 | 311 | 0 | 0 | 311 |  |
| TPR | 1116132 | 228 | 0 | 0 | 228 |  |
| IQV | 1478242 | 212 | 0 | 0 | 212 |  |
| EL | 1001250 | 439 | 0 | 0 | 439 |  |
| AEE | 1002910 | 289 | 0 | 0 | 289 |  |
| BR | 1383312 | 437 | 0 | 0 | 437 |  |
| FANG | 1539838 | 367 | 0 | 0 | 367 |  |
| GIS | 40704 | 357 | 0 | 0 | 357 |  |
| VLTO | 1967680 | 250 | 0 | 0 | 250 |  |
| PPG | 79879 | 791 | 0 | 0 | 791 |  |
| UAL | 100517 | 273 | 0 | 0 | 273 |  |
| VMRK | 906107 | 314 | 0 | 0 | 314 |  |
| TYL | 860731 | 331 | 0 | 0 | 331 |  |
| ADM | 7084 | 449 | 0 | 0 | 449 |  |
| CCL | 815097 | 190 | 0 | 0 | 190 |  |
| SBAC | 1034054 | 222 | 0 | 0 | 222 |  |
| PPL | 922224 | 349 | 0 | 0 | 349 |  |
| DOV | 29905 | 169 | 0 | 0 | 169 |  |
| STZ | 16918 | 292 | 0 | 0 | 292 |  |
| GDDY | 1609711 | 358 | 0 | 0 | 358 |  |
| MKL | 1096343 | 257 | 0 | 0 | 257 |  |
| SYF | 1601712 | 633 | 0 | 0 | 633 |  |
| MPWR | 1280452 | 482 | 0 | 0 | 482 |  |
| HSY | 47111 | 533 | 0 | 0 | 533 |  |
| IP | 51434 | 272 | 0 | 0 | 272 |  |
| LEN | 920760 | 265 | 0 | 0 | 265 |  |
| ATO | 731802 | 214 | 0 | 0 | 214 |  |
| CBOE | 1374310 | 237 | 0 | 0 | 237 |  |
| STE | 1757898 | 247 | 0 | 0 | 247 |  |
| MTD | 1037646 | 165 | 0 | 0 | 165 |  |
| HPQ | 47217 | 256 | 0 | 0 | 256 |  |
| HBAN | 49196 | 772 | 0 | 0 | 772 |  |
| NTRS | 73124 | 466 | 0 | 0 | 466 |  |
| LYV | 1335258 | 240 | 0 | 0 | 240 |  |
| FITB | 35527 | 378 | 0 | 0 | 378 |  |
| CNP | 1130310 | 214 | 0 | 0 | 214 |  |
| TDY | 1094285 | 222 | 0 | 0 | 222 |  |
| AWK | 1410636 | 256 | 0 | 0 | 256 |  |
| IBKR | 1381197 | 214 | 0 | 0 | 214 |  |
| ES | 72741 | 225 | 0 | 0 | 225 |  |
| CDW | 1402057 | 380 | 0 | 0 | 380 |  |
| FE | 1031296 | 236 | 0 | 0 | 236 |  |
| BAM | 1937926 | 83 | 0 | 0 | 83 |  |
| ON | 1097864 | 215 | 0 | 0 | 215 |  |
| TOST | 1650164 | 646 | 0 | 0 | 646 |  |
| CHD | 313927 | 769 | 0 | 0 | 769 |  |
| CINF | 20286 | 334 | 0 | 0 | 334 |  |
| CPAY | 1175454 | 252 | 0 | 0 | 252 |  |
| WSM | 719955 | 333 | 0 | 0 | 333 |  |
| SW | 2005951 | 363 | 0 | 0 | 363 |  |
| PODD | 1145197 | 279 | 0 | 0 | 279 |  |
| TSCO | 916365 | 292 | 0 | 0 | 292 |  |
| KHC | 1637459 | 200 | 0 | 0 | 200 |  |
| WRB | 11544 | 257 | 0 | 0 | 257 |  |
| DLTR | 935703 | 259 | 0 | 0 | 259 |  |
| NTRA | 1604821 | 748 | 0 | 0 | 748 |  |
| LH | 920148 | 396 | 0 | 0 | 396 |  |
| HUBB | 48898 | 266 | 0 | 0 | 266 |  |
| QSR | 1618756 | 426 | 0 | 0 | 426 |  |
| RDDT | 1713445 | 427 | 0 | 0 | 427 |  |
| HPE | 1645590 | 444 | 0 | 0 | 444 |  |
| DG | 29534 | 231 | 0 | 0 | 231 |  |
| FLEX | 866374 | 439 | 0 | 0 | 439 |  |
| INSM | 1104506 | 526 | 0 | 0 | 526 |  |
| LDOS | 1336920 | 402 | 0 | 0 | 402 |  |
| WAT | 1000697 | 211 | 0 | 0 | 211 |  |
| TROW | 1113169 | 334 | 0 | 0 | 334 |  |
| AFRM | 1820953 | 386 | 0 | 0 | 386 |  |
| PHM | 822416 | 160 | 0 | 0 | 160 |  |
| CMS | 811156 | 231 | 0 | 0 | 231 |  |
| RF | 1281761 | 263 | 0 | 0 | 263 |  |
| NVR | 906163 | 179 | 0 | 0 | 179 |  |
| DVN | 1090012 | 213 | 0 | 0 | 213 |  |
| INVH | 1687229 | 170 | 0 | 0 | 170 |  |
| DRI | 940944 | 379 | 0 | 0 | 379 |  |
| DGX | 1022079 | 357 | 0 | 0 | 357 |  |
| SOFI | 1818874 | 435 | 0 | 0 | 435 |  |
| TPL | 1811074 | 891 | 0 | 0 | 891 |  |
| Q | 2058873 | 117 | 0 | 0 | 117 |  |
| EXPE | 1324424 | 299 | 0 | 0 | 299 |  |
| CLX | 21076 | 264 | 0 | 0 | 264 |  |
| EIX | 827052 | 258 | 0 | 0 | 258 |  |
| ZM | 1585521 | 394 | 0 | 0 | 394 |  |
| USFD | 1665918 | 255 | 0 | 0 | 255 |  |
| EXE | 895126 | 216 | 0 | 0 | 216 |  |
| RBA | 1046102 | 484 | 0 | 0 | 484 |  |
| KEY | 91576 | 351 | 0 | 0 | 351 |  |
| MKC | 63754 | 491 | 0 | 0 | 491 |  |
| GPN | 1123360 | 213 | 0 | 0 | 213 |  |
| AMCR | 1748790 | 288 | 0 | 0 | 288 |  |
| CFG | 759944 | 350 | 0 | 0 | 350 |  |
| CASY | 726958 | 191 | 0 | 0 | 191 |  |
| MDB | 1441816 | 465 | 0 | 0 | 465 |  |
| DKNG | 1883685 | 544 | 0 | 0 | 544 |  |
| NI | 1111711 | 233 | 0 | 0 | 233 |  |
| IFF | 51253 | 246 | 0 | 0 | 246 |  |
| TRMB | 864749 | 354 | 0 | 0 | 354 |  |
| DOW | 1751788 | 228 | 0 | 0 | 228 |  |
| TWLO | 1447669 | 411 | 0 | 0 | 411 |  |
| PINS | 1506293 | 496 | 0 | 0 | 496 |  |
| FIX | 1035983 | 285 | 0 | 0 | 285 |  |
| PTC | 857005 | 255 | 0 | 0 | 255 |  |
| WY | 106535 | 248 | 0 | 0 | 248 |  |
| ZS | 1713683 | 344 | 0 | 0 | 344 |  |
| BIIB | 875045 | 229 | 0 | 0 | 229 |  |
| AVAV | 1368622 | 258 | 0 | 0 | 258 |  |
| LII | 1069202 | 262 | 0 | 0 | 262 |  |
| FTV | 1659166 | 352 | 0 | 0 | 352 |  |
| TEVA | 818686 | 336 | 0 | 0 | 336 |  |
| ESS | 920522 | 173 | 0 | 0 | 173 |  |
| ZBH | 1136869 | 357 | 0 | 0 | 357 |  |
| CLS | 1030894 | 243 | 0 | 0 | 243 |  |
| PFG | 1126328 | 523 | 0 | 0 | 523 |  |
| FSLR | 1274494 | 522 | 0 | 0 | 522 |  |
| LULU | 1397187 | 268 | 0 | 0 | 268 |  |
| FDS | 1013237 | 295 | 0 | 0 | 295 |  |
| SSNC | 1402436 | 176 | 0 | 0 | 176 |  |
| TSN | 100493 | 234 | 0 | 0 | 234 |  |
| FCNCA | 798941 | 203 | 0 | 0 | 203 |  |
| EME | 105634 | 245 | 0 | 0 | 245 |  |
| BURL | 1579298 | 247 | 0 | 0 | 247 |  |
| NTAP | 1002047 | 388 | 0 | 0 | 388 |  |
| FN | 1408710 | 195 | 0 | 0 | 195 |  |
| TRU | 1552033 | 374 | 0 | 0 | 374 |  |
| KEYS | 1601046 | 317 | 0 | 0 | 317 |  |
| P | 1474432 | 367 | 0 | 0 | 367 |  |
| GPC | 40987 | 277 | 0 | 0 | 277 |  |
| EQH | 1333986 | 444 | 0 | 0 | 444 |  |
| TW | 1758730 | 267 | 0 | 0 | 267 |  |
| LUV | 92380 | 279 | 0 | 0 | 279 |  |
| ULTA | 1403568 | 157 | 0 | 0 | 157 |  |
| RPRX | 1802768 | 276 | 0 | 0 | 276 |  |
| PKG | 75677 | 222 | 0 | 0 | 222 |  |
| PNR | 77360 | 209 | 0 | 0 | 209 |  |
| YUMC | 1673358 | 361 | 0 | 0 | 361 |  |
| LITE | 1633978 | 396 | 0 | 0 | 396 |  |
| RS | 861884 | 157 | 0 | 0 | 157 |  |
| CW | 26324 | 291 | 0 | 0 | 291 |  |
| VRSN | 1014473 | 405 | 0 | 0 | 405 |  |
| OKTA | 1660134 | 379 | 0 | 0 | 379 |  |
| COO | 711404 | 191 | 0 | 0 | 191 |  |
| BAX | 10456 | 216 | 0 | 0 | 216 |  |
| MOH | 1179929 | 274 | 0 | 0 | 274 |  |
| SNA | 91440 | 257 | 0 | 0 | 257 |  |
| LOGI | 1032975 | 168 | 0 | 0 | 168 |  |
| ROL | 84839 | 246 | 0 | 0 | 246 |  |
| CSL | 790051 | 315 | 0 | 0 | 315 |  |
| SFM | 1575515 | 454 | 0 | 0 | 454 |  |
| SUI | 912593 | 267 | 0 | 0 | 267 |  |
| WST | 105770 | 163 | 0 | 0 | 163 |  |
| CRS | 17843 | 250 | 0 | 0 | 250 |  |
| EVRG | 1711269 | 193 | 0 | 0 | 193 |  |
| WSO | 105016 | 134 | 0 | 0 | 134 |  |
| GEN | 849399 | 182 | 0 | 0 | 182 |  |
| LNT | 352541 | 184 | 0 | 0 | 184 |  |
| ZBRA | 877212 | 280 | 0 | 0 | 280 |  |
| ARCC | 1287750 | 109 | 0 | 0 | 109 |  |
| EXPD | 746515 | 266 | 0 | 0 | 266 |  |
| L | 60086 | 360 | 0 | 0 | 360 |  |
| FFIV | 1048695 | 447 | 0 | 0 | 447 |  |
| DPZ | 1286681 | 319 | 0 | 0 | 319 |  |
| BALL | 9389 | 281 | 0 | 0 | 281 |  |
| HAL | 45012 | 361 | 0 | 0 | 361 |  |
| SMCI | 1375365 | 401 | 0 | 0 | 401 |  |
| DOCU | 1261333 | 468 | 0 | 0 | 468 |  |
| UAA | 1336917 | 289 | 0 | 0 | 289 |  |
| ZG | 1617640 | 576 | 0 | 0 | 576 |  |
| RKLB | 1819994 | 336 | 0 | 0 | 336 |  |
| LYB | 1489393 | 296 | 0 | 0 | 296 |  |
| CF | 1324404 | 288 | 0 | 0 | 288 |  |
| APTV | 1521332 | 231 | 0 | 0 | 231 |  |
| DECK | 910521 | 310 | 0 | 0 | 310 |  |
| ONC | 1651308 | 412 | 0 | 0 | 412 |  |
| DT | 1773383 | 355 | 0 | 0 | 355 |  |
| BJ | 1531152 | 246 | 0 | 0 | 246 |  |
| J | 52988 | 250 | 0 | 0 | 250 |  |
| JBL | 898293 | 436 | 0 | 0 | 436 |  |
| XPO | 1166003 | 201 | 0 | 0 | 201 |  |
| TXT | 217346 | 163 | 0 | 0 | 163 |  |
| EG | 1095073 | 224 | 0 | 0 | 224 |  |
| RIVN | 1874178 | 321 | 0 | 0 | 321 |  |
| GGG | 42888 | 294 | 0 | 0 | 294 |  |
| KIM | 879101 | 166 | 0 | 0 | 166 |  |
| SN | 1957132 | 118 | 0 | 0 | 118 |  |
| UNM | 5513 | 219 | 0 | 0 | 219 |  |
| FNF | 1331875 | 234 | 0 | 0 | 234 |  |
| OMC | 29989 | 289 | 0 | 0 | 289 |  |
| EWBC | 1069157 | 223 | 0 | 0 | 223 |  |
| SGI | 1206264 | 223 | 0 | 0 | 223 |  |
| QXO | 1236275 | 320 | 0 | 0 | 320 |  |
| TKO | 1973266 | 339 | 0 | 0 | 339 |  |
| AVY | 8818 | 222 | 0 | 0 | 222 |  |
| WPC | 1025378 | 189 | 0 | 0 | 189 |  |
| CG | 1527166 | 321 | 0 | 0 | 321 |  |
| RPM | 110621 | 188 | 0 | 0 | 188 |  |
| MAS | 62996 | 189 | 0 | 0 | 189 |  |
| DUOL | 1562088 | 445 | 0 | 0 | 445 |  |
| TLN | 1622536 | 163 | 0 | 0 | 163 |  |
| RBRK | 1943896 | 376 | 0 | 0 | 376 |  |
| IEX | 832101 | 134 | 0 | 0 | 134 |  |
| BWXT | 1486957 | 283 | 0 | 0 | 283 |  |
| ALAB | 1736297 | 377 | 0 | 0 | 377 |  |
| RGA | 898174 | 234 | 0 | 0 | 234 |  |
| SOLV | 1964738 | 199 | 0 | 0 | 199 |  |
| JKHY | 779152 | 196 | 0 | 0 | 196 |  |
| LVS | 1300514 | 197 | 0 | 0 | 197 |  |
| STLD | 1022671 | 402 | 0 | 0 | 402 |  |
| MDLN | 2046386 | 101 | 0 | 0 | 101 |  |

## Without usable revenue (files written, flagged; nothing is dropped)

- SPCX SPACE EXPLORATION TECHNOLOGIES CORP: no_revenue (file written, flagged)
- ENB ENBRIDGE INC: reports_in_CAD (file written, flagged)
- CP CANADIAN PACIFIC KANSAS CITY LTD/CN: reports_in_CAD (file written, flagged)
- HONA Honeywell Aerospace Inc.: no_revenue (file written, flagged)
- ARCC ARES CAPITAL CORP: no_revenue (file written, flagged)
- MBGL Mobility Global Inc.: no_revenue (file written, flagged)
- CLBK Columbia Financial, Inc./MD/: no_revenue (file written, flagged)
- NLY ANNALY CAPITAL MANAGEMENT INC: no_revenue (file written, flagged)
- CBRS Cerebras Systems Inc.: no_revenue (file written, flagged)
- FRBT Forbright, Inc.: no_revenue (file written, flagged)
- MAIR Madison Air Solutions Corp: no_revenue (file written, flagged)
- GMRS GMR Solutions Inc.: no_revenue (file written, flagged)
- OBDC Blue Owl Capital Corp: no_revenue (file written, flagged)
- ARXS Arxis, Inc.: no_revenue (file written, flagged)
- OKLO Oklo Inc.: no_revenue (file written, flagged)
- BXSL Blackstone Secured Lending Fund: no_revenue (file written, flagged)
- OTF Blue Owl Technology Finance Corp.: no_revenue (file written, flagged)
- OCTV Octave Intelligence plc: no_revenue (file written, flagged)
- APA APA Corp: no_revenue (file written, flagged)
- BTGO BITGO HOLDINGS, INC.: no_revenue (file written, flagged)
- CSQR Csquare, Inc.: no_revenue (file written, flagged)
- FSK FS KKR Capital Corp: no_revenue (file written, flagged)
- INIO INNIO N.V.: no_revenue (file written, flagged)
- VGNT Versigent PLC: no_revenue (file written, flagged)
- MAIN Main Street Capital CORP: no_revenue (file written, flagged)
- JAN Janus Living, Inc.: no_revenue (file written, flagged)
- ADIG ADI GLOBAL DISTRIBUTION INC.: no_revenue (file written, flagged)
- MC Moelis & Co: no_revenue (file written, flagged)
- GBDC GOLUB CAPITAL BDC, Inc.: no_revenue (file written, flagged)
- PCVX Vaxcyte, Inc.: no_revenue (file written, flagged)
- NUVL Nuvalent, Inc.: no_revenue (file written, flagged)
- FRVO Fervo Energy Co: no_revenue (file written, flagged)
- FCBM First Carolina Financial Services, Inc.: no_revenue (file written, flagged)
- HTGC Hercules Capital, Inc.: no_revenue (file written, flagged)
- QNT Quantinuum Inc.: no_revenue (file written, flagged)
- QS QuantumScape Corp: no_revenue (file written, flagged)
- PBAM Private Bancorp of America, Inc.: no_revenue (file written, flagged)
- XE X-Energy, Inc.: no_revenue (file written, flagged)
- BANR BANNER CORP: no_revenue (file written, flagged)
- TSLX Sixth Street Specialty Lending, Inc.: no_revenue (file written, flagged)
- MWH SOLV Energy, Inc.: no_revenue (file written, flagged)
- YSS York Space Systems Inc.: no_revenue (file written, flagged)
- YSWY Yesway, Inc.: no_revenue (file written, flagged)
- LFTO Liftoff Mobile, Inc.: no_revenue (file written, flagged)
- BXDC Blackstone Digital Infrastructure Trust Inc.: no_revenue (file written, flagged)
- BOBS Bob's Discount Furniture, Inc.: no_revenue (file written, flagged)
- DPC DPC Holdings PLC: no_revenue (file written, flagged)
- PS PERSHING SQUARE INC.: no_revenue (file written, flagged)
- LMRI Lumexa Imaging Holdings, Inc.: no_revenue (file written, flagged)
- EROK EagleRock Land, LLC: no_revenue (file written, flagged)
- FRMI Fermi Inc.: no_revenue (file written, flagged)
- APGE Apogee Therapeutics, Inc.: no_revenue (file written, flagged)
- NVRI Enviri Corp: no_revenue (file written, flagged)
- TMC TMC the metals Co Inc.: no_revenue (file written, flagged)
- MSDL Morgan Stanley Direct Lending Fund: no_revenue (file written, flagged)
- AADX Applied Aerospace & Defense, Inc.: no_revenue (file written, flagged)
- DX DYNEX CAPITAL INC: no_revenue (file written, flagged)
- ARR Armour Residential REIT, Inc.: no_revenue (file written, flagged)
- MFP Midera Food Processing, Inc.: no_revenue (file written, flagged)
- IRON Disc Medicine, Inc.: no_revenue (file written, flagged)
- APC ARKO Petroleum Corp.: no_revenue (file written, flagged)
- HMH HMH Holding Inc: no_revenue (file written, flagged)
- MLTX MoonLake Immunotherapeutics: no_revenue (file written, flagged)
- AIAI AIAI Holdings Corp: no_revenue (file written, flagged)
- VERA Vera Therapeutics, Inc.: no_revenue (file written, flagged)
- FETH Fidelity Ethereum Fund: no_revenue (file written, flagged)
- IMVT Immunovant, Inc.: no_revenue (file written, flagged)
- GSBD Goldman Sachs BDC, Inc.: no_revenue (file written, flagged)
- OCSL Oaktree Specialty Lending Corp: no_revenue (file written, flagged)
- KLRA Kailera Therapeutics, Inc.: no_revenue (file written, flagged)
- EWTX Edgewise Therapeutics, Inc.: no_revenue (file written, flagged)
- LIME Neutron Holdings, Inc.: no_revenue (file written, flagged)
- PBLS Parabilis Medicines, Inc.: no_revenue (file written, flagged)
- CIM CHIMERA INVESTMENT CORP: no_revenue (file written, flagged)
- TWOD TWO HARBORS INVESTMENT CORP.: no_revenue (file written, flagged)
- PFLT PennantPark Floating Rate Capital Ltd.: no_revenue (file written, flagged)
- ITG ITG, Inc./DE/: no_revenue (file written, flagged)
- BHVN Biohaven Ltd.: no_revenue (file written, flagged)
- REF Reformation Inc.: no_revenue (file written, flagged)
- LCLN Lincoln International, Inc.: no_revenue (file written, flagged)
- NMFC New Mountain Finance Corp: no_revenue (file written, flagged)
- EROC ERock, Inc.: no_revenue (file written, flagged)
- AVEX AEVEX Corp.: no_revenue (file written, flagged)
- DYN Dyne Therapeutics, Inc.: no_revenue (file written, flagged)
- CGBD Carlyle Secured Lending, Inc.: no_revenue (file written, flagged)
- IOND Ionic Digital Inc.: no_revenue (file written, flagged)
- TRIN Trinity Capital Inc.: no_revenue (file written, flagged)
- HAWK HawkEye 360, Inc.: no_revenue (file written, flagged)
- PSEC PROSPECT CAPITAL CORP: no_revenue (file written, flagged)
- ORC Orchid Island Capital, Inc.: no_revenue (file written, flagged)
- PPTA PERPETUA RESOURCES CORP.: no_revenue (file written, flagged)
- ORIC Oric Pharmaceuticals, Inc.: no_revenue (file written, flagged)
- ELVN Enliven Therapeutics, Inc.: no_revenue (file written, flagged)
- GPCR Structure Therapeutics Inc.: no_revenue (file written, flagged)
- BBDC Barings BDC, Inc.: no_revenue (file written, flagged)
- MANE Veradermics, Inc: no_revenue (file written, flagged)
- SLRC SLR Investment Corp.: no_revenue (file written, flagged)
- EIKN Eikon Therapeutics, Inc.: no_revenue (file written, flagged)
- AVBP ArriVent BioPharma, Inc.: no_revenue (file written, flagged)
- BRUN Boost Run Inc.: no_revenue (file written, flagged)
- KARD Kardigan, Inc.: no_revenue (file written, flagged)
- RMIX Suncrete, Inc.: no_revenue (file written, flagged)
- PXED Phoenix Education Partners, Inc.: no_revenue (file written, flagged)
- ADAM ADAMAS TRUST, INC.: no_revenue (file written, flagged)
- GENB Generate Biomedicines, Inc.: no_revenue (file written, flagged)
- AKTS Aktis Oncology, Inc.: no_revenue (file written, flagged)
- WHK WhiteHawk Minerals Corp.: no_revenue (file written, flagged)
- DMII Drugs Made In America Acquisition II Corp.: no_revenue (file written, flagged)
- ODTX Odyssey Therapeutics, Inc.: no_revenue (file written, flagged)
- BCSS Bain Capital GSS Investment Corp.: no_revenue (file written, flagged)
- COAG Hemab Therapeutics Holdings, Inc.: no_revenue (file written, flagged)
- SPTX Seaport Therapeutics, Inc.: no_revenue (file written, flagged)
- AVLN Avalyn Pharma Inc.: no_revenue (file written, flagged)
- SUJA SUJA LIFE, INC.: no_revenue (file written, flagged)
- CXII Churchill Capital Corp XII: no_revenue (file written, flagged)
- GCGR General Catalyst Global Resilience Merger Corp.: no_revenue (file written, flagged)
- ALMR Alamar Biosciences, Inc.: no_revenue (file written, flagged)
- MPLT MapLight Therapeutics, Inc.: no_revenue (file written, flagged)
- MLAA Mountain Lake Acquisition Corp. II: no_revenue (file written, flagged)
- LBRX LB PHARMACEUTICALS INC: no_revenue (file written, flagged)
- GHXIU Gores Holdings XI, Inc.: no_revenue (file written, flagged)
- BRR Silvia, Inc.: no_revenue (file written, flagged)
- KRSP Rice Acquisition Corp 3: no_revenue (file written, flagged)
- IACO Idea Acquisition Corp.: no_revenue (file written, flagged)
- AEXA American Exceptionalism Acquisition Corp. A: no_revenue (file written, flagged)
- APXT Apex Treasury Corp: no_revenue (file written, flagged)
- CRAN Crane Harbor Acquisition Corp. II: no_revenue (file written, flagged)
- NWAX New America Acquisition I Corp.: no_revenue (file written, flagged)
- MESH Meshflow Acquisition Corp: no_revenue (file written, flagged)
- KBON Karbon Capital Partners Corp.: no_revenue (file written, flagged)
- KRAQ KRAKacquisition Corp: no_revenue (file written, flagged)
- IEAG Infinite Eagle Acquisition Corp.: no_revenue (file written, flagged)
- SSMR Sunshine Silver Mining & Refining Co: no_revenue (file written, flagged)
- GUAC Berto Acquisition Corp. II: no_revenue (file written, flagged)
- MEVO M Evo Global Acquisition Corp II: no_revenue (file written, flagged)
- MZYX MOZAYYX Acquisition Corp.: no_revenue (file written, flagged)
- ALOV Aldabra 4 Liquidity Opportunity Vehicle, Inc.: no_revenue (file written, flagged)
- CLBR Colombier Acquisition Corp. III: no_revenue (file written, flagged)
- BBCQ Bleichroeder Acquisition Corp. II: no_revenue (file written, flagged)
- ZKP Lafayette Digital Acquisition Corp. I: no_revenue (file written, flagged)
- OIM OneIM Acquisition Corp.: no_revenue (file written, flagged)
- FVAV Fortress Value Acquisition Corp. V: no_revenue (file written, flagged)
- DBCA D. Boral Acquisition I Corp.: no_revenue (file written, flagged)
- HACQ HCM IV Acquisition Corp.: no_revenue (file written, flagged)
- KEYY Keystone Acquisition Corp.: no_revenue (file written, flagged)
- BCARU D. Boral ARC Acquisition I Corp.: no_revenue (file written, flagged)
- ACAA Averin Capital Acquisition Corp.: no_revenue (file written, flagged)
- ELMT Elmet Group Co.: no_revenue (file written, flagged)
- ARCI Archimedes Tech SPAC Partners III Co.: no_revenue (file written, flagged)
- RNA Atrium Therapeutics, Inc.: no_revenue (file written, flagged)
- CGCFU Cartesian Growth Corp IV: no_revenue (file written, flagged)
- CCII Cohen Circle Acquisition Corp. II: no_revenue (file written, flagged)
- HCMA HCM III ACQUISITION CORP.: no_revenue (file written, flagged)
- BDCI BTC Development Corp.: no_revenue (file written, flagged)
- ARTC Art Technology Acquisition Corp.: no_revenue (file written, flagged)
- SORN Soren Acquisition Corp.: no_revenue (file written, flagged)
- TLNC Talon Capital Corp.: no_revenue (file written, flagged)
- GIX GigCapital9 Corp.: no_revenue (file written, flagged)
- IPFX Inflection Point Acquisition Corp. VI: no_revenue (file written, flagged)
- CAII Collective Acquisition Corp. II: no_revenue (file written, flagged)
- DSAC Daedalus Special Acquisition Corp.: no_revenue (file written, flagged)
- IACQ Irenic Acquisition Corp.: no_revenue (file written, flagged)
- AACI Armada Acquisition Corp. III: no_revenue (file written, flagged)
- RREV RRE Ventures Acquisition Corp.: no_revenue (file written, flagged)
- CAES Cantor Equity Partners VII, Inc.: no_revenue (file written, flagged)
- EVOX Evolution Global Acquisition Corp: no_revenue (file written, flagged)
- SGP SpyGlass Pharma, Inc.: no_revenue (file written, flagged)
- XRPN Armada Acquisition Corp. II: no_revenue (file written, flagged)
- KOYN CSLM Digital Asset Acquisition Corp III, Ltd: no_revenue (file written, flagged)
- RNGT Range Capital Acquisition Corp II: no_revenue (file written, flagged)
- VHCP Vine Hill Capital Investment Corp. II: no_revenue (file written, flagged)
- VACI Viking Acquisition Corp I: no_revenue (file written, flagged)
- SAC Safeguard Acquisition Corp.: no_revenue (file written, flagged)
- GPAC General Purpose Acquisition Corp.: no_revenue (file written, flagged)
- ADAC American Drive Acquisition Co: no_revenue (file written, flagged)
- ITHA ITHAX Acquisition Corp III: no_revenue (file written, flagged)
- QLEP Quantum Leap Acquisition Corp: no_revenue (file written, flagged)
- LEGO Legato Merger Corp. IV: no_revenue (file written, flagged)
- SAAQ Space Asset Acquisition Corp.: no_revenue (file written, flagged)
- KCAC-UN Kensington Capital Acquisition Corp. VI: no_revenue (file written, flagged)
- MTAL Metals Acquisition Corp. II: no_revenue (file written, flagged)
- IPXG Inflection Point Acquisition Corp. VII: no_revenue (file written, flagged)
- CAQ Cambridge Acquisition Corp.: no_revenue (file written, flagged)
- AACO Abony Acquisition Corp. I: no_revenue (file written, flagged)
- SVIV Spring Valley Acquisition Corp. IV: no_revenue (file written, flagged)
- TMTS Spartacus Acquisition Corp. II: no_revenue (file written, flagged)
- IRHO Iron Horse Acquisition II Corp.: no_revenue (file written, flagged)
- KPET KPET Ultra Paceline Corp: no_revenue (file written, flagged)
- ILLU Illumination Acquisition Corp. I: no_revenue (file written, flagged)
- GSRV GSR V Acquisition Corp.: no_revenue (file written, flagged)
- USDE StableCoinX Inc.: no_revenue (file written, flagged)
- FGII FG Imperii Acquisition Corp.: no_revenue (file written, flagged)
- FTRA FutureCorp Space Acquisition 1: no_revenue (file written, flagged)
- YICC Yorkville International Capital Corp.: no_revenue (file written, flagged)
- WLCOU Wilco 63 Corp: no_revenue (file written, flagged)
- XCBE X3 Acquisition Corp. Ltd.: no_revenue (file written, flagged)
- ISNR Snow Rothschild Acquisition Corp.: no_revenue (file written, flagged)
- BIXI Bitcoin Infrastructure Acquisition Corp Ltd: no_revenue (file written, flagged)
- MTNE CH4 Natural Solutions Corp: no_revenue (file written, flagged)
- SIND Sinda Ltd.: no_revenue (file written, flagged)
- SVAQ Silicon Valley Acquisition Corp.: no_revenue (file written, flagged)
- ACGC ACP Holdings Acquisition Corp.: no_revenue (file written, flagged)
- SHOT RMG ML Sports Holdings: no_revenue (file written, flagged)
- QMLS QumulusAI, Inc.: no_revenue (file written, flagged)
- HCAC Hall Chadwick Acquisition Corp: no_revenue (file written, flagged)
- TRGS TRG Latin America Acquisitions Corp.: no_revenue (file written, flagged)
- XSLL Xsolla SPAC 1: no_revenue (file written, flagged)
- PAII Pyrophyte Acquisition Corp. II: no_revenue (file written, flagged)
- DNMX Dynamix Corp III: no_revenue (file written, flagged)
- MUZE Muzero Acquisition Corp: no_revenue (file written, flagged)
- VEL Velocity Financial, Inc.: no_revenue (file written, flagged)
- NHIV NewHold Investment Corp IV: no_revenue (file written, flagged)
- IPVV InterPrivate Investment Partners V, Inc.: no_revenue (file written, flagged)
- OFRM Once Upon a Farm, PBC: no_revenue (file written, flagged)
- QADR QDRO Acquisition Corp.: no_revenue (file written, flagged)
- APMD Apnimed, Inc.: no_revenue (file written, flagged)
- MOBI Mobia Medical, Inc.: no_revenue (file written, flagged)
- PARK Park Dental Partners, Inc.: no_revenue (file written, flagged)
- OHAC Oceanhawk Acquisition Corp.: no_revenue (file written, flagged)
- TRAX First Tracks Biotherapeutics, Inc.: no_revenue (file written, flagged)
- GTERA Globa Terra Acquisition Corp: no_revenue (file written, flagged)
- MKLY McKinley Acquisition Corp: no_revenue (file written, flagged)
- PTAC Patriot Acquisition Corp./CI: no_revenue (file written, flagged)
- DYOR Insight Digital Partners II: no_revenue (file written, flagged)
- TDWD Tailwind 2.0 Acquisition Corp.: no_revenue (file written, flagged)
- IGAC Invest Green Acquisition Corp: no_revenue (file written, flagged)
- BLRK Bluerock Acquisition Corp.: no_revenue (file written, flagged)
- BIII Black Spade Acquisition III Co: no_revenue (file written, flagged)
- LTGR Long Table Growth Corp.: no_revenue (file written, flagged)
- SUMA SUMA Acquisition Corp: no_revenue (file written, flagged)
- SSAC SPACSphere Acquisition Corp.: no_revenue (file written, flagged)
- AACP Apogee Acquisition Corp: no_revenue (file written, flagged)
- TVIV Texas Ventures Acquisition IV Corp: no_revenue (file written, flagged)
- SWRD Stewards, Inc.: no_revenue (file written, flagged)
- ATLQ JAB Acquisition Corp I: no_revenue (file written, flagged)
- IRAB Iris Acquisition Corp II: no_revenue (file written, flagged)
- PALO PALOMA ACQUISITION CORP I: no_revenue (file written, flagged)
- DGAC DISCIPLINED GROWTH ACQUISITION Corp: no_revenue (file written, flagged)
- IDAC Iron Dome Acquisition I Corp.: no_revenue (file written, flagged)
- BEBE TGE Value Creative Solutions Corp: no_revenue (file written, flagged)
- ETSS Energy Transition Special Opportunities: no_revenue (file written, flagged)
- HAVA Harvard Ave Acquisition Corp: no_revenue (file written, flagged)
- LFAC Leapfrog Acquisition Corp: no_revenue (file written, flagged)
- WLII Willow Lane Acquisition Corp. II: no_revenue (file written, flagged)
- STDN Standard Nuclear, Inc.: no_revenue (file written, flagged)
- APMC AmperCap Acquisition Co: no_revenue (file written, flagged)
- AESP Aeon Acquisition I Corp.: no_revenue (file written, flagged)
- AIIA AI Infrastructure Acquisition Corp.: no_revenue (file written, flagged)
- BID Tribeca Strategic Acquisition Corp.: no_revenue (file written, flagged)
- KTWO K2 Capital Acquisition Corp: no_revenue (file written, flagged)
- PAAC Proem Acquisition Corp. I: no_revenue (file written, flagged)
- BWIV Blue Water Acquisition Corp. IV: no_revenue (file written, flagged)
- CHEC Chenghe Acquisition III Co.: no_revenue (file written, flagged)
- ATTO Attovia Therapeutics, Inc.: no_revenue (file written, flagged)
- CTAA Clearthink 1 Acquisition Corp.: no_revenue (file written, flagged)
- BRVE Braveheart Bio, Inc.: no_revenue (file written, flagged)
- BLSM BlossomHill Therapeutics, Inc.: no_revenue (file written, flagged)
- ARCL ARC Group Acquisition I Corp.: no_revenue (file written, flagged)
- PONO Pono Capital Four, Inc.: no_revenue (file written, flagged)
- INAC Indigo Acquisition Corp.: no_revenue (file written, flagged)
- NMP NMP Acquisition Corp.: no_revenue (file written, flagged)
- SPEG Silver Pegasus Acquisition Corp.: no_revenue (file written, flagged)
- EMIS Emmis Acquisition Corp.: no_revenue (file written, flagged)
- WPAC White Pearl Acquisition Corp.: no_revenue (file written, flagged)
- LAFA LaFayette Acquisition Corp.: no_revenue (file written, flagged)
- LKSP Lake Superior Acquisition Corp: no_revenue (file written, flagged)
- WENC West Enclave Merger Corp.: no_revenue (file written, flagged)
- QRED QuasarEdge Acquisition Corp: no_revenue (file written, flagged)
- GLED GalaxyEdge Acquisition Corp: no_revenue (file written, flagged)
- CEPS Cantor Equity Partners VI, Inc.: no_revenue (file written, flagged)
- ALPX Alpex Acquisition Corp: no_revenue (file written, flagged)
- NREF NexPoint Real Estate Finance, Inc.: no_revenue (file written, flagged)
- TRAD APEX Tech Acquisition Inc.: no_revenue (file written, flagged)
- FMAC Future Money Acquisition Corp: no_revenue (file written, flagged)
- AVAT Avalanche Treasury Corp: no_revenue (file written, flagged)
- PLUN Plutonian Acquisition Corp. II: no_revenue (file written, flagged)
- OTAI Starlink AI Acquisition Corp: no_revenue (file written, flagged)
- UAC United Acquisition Corp. I: no_revenue (file written, flagged)
- APUR Aperture AC: no_revenue (file written, flagged)
- SBMT SILVER BOW MINING CORP.: no_revenue (file written, flagged)
- SCPQ Social Commerce Partners Corp: no_revenue (file written, flagged)
- REA Rare Earths Americas, Inc.: no_revenue (file written, flagged)
- RFAM RF Acquisition Corp III: no_revenue (file written, flagged)
- FTHA Forefront Tech Holdings Acquisition Corp: no_revenue (file written, flagged)
- VECA Vernal Capital Acquisition Corp.: no_revenue (file written, flagged)
- BHAV BHAV Acquisition Corp: no_revenue (file written, flagged)
- XFLH XFLH Capital Corp: no_revenue (file written, flagged)
- MYX Maywood Acquisition Corp. 2: no_revenue (file written, flagged)
- NKLR Terra Innovatum Global N.V.: no_revenue (file written, flagged)
- FXAC FortuneX Acquisition Corp: no_revenue (file written, flagged)
- FWAC Futurewave Acquisition Corp: no_revenue (file written, flagged)
- BRKH Burtech Acquisition Corp II: no_revenue (file written, flagged)
- CHPG ChampionsGate Acquisition Corp: no_revenue (file written, flagged)
- AMAN Amanat Acquisition Corp.: no_revenue (file written, flagged)
- RACC Research Alliance Corp III: no_revenue (file written, flagged)
- ORIQ Origin Investment Corp I: no_revenue (file written, flagged)
- MMTX Miluna Acquisition Corp: no_revenue (file written, flagged)
- GFUZ General Fusion Group Ltd.: no_revenue (file written, flagged)
- GLND Greenland Energy Co: no_revenue (file written, flagged)
- LTGO Latigo Biotherapeutics, Inc.: no_revenue (file written, flagged)
- JATT JATT II Acquisition Corp.: no_revenue (file written, flagged)
- ALIS Calisa Acquisition Corp: no_revenue (file written, flagged)
- PECE Peace Acquisition Corp.: no_revenue (file written, flagged)
- MCAH Mountain Crest Acquisition 6 Corp.: no_revenue (file written, flagged)
- NBRG Newbridge Acquisition Ltd: no_revenue (file written, flagged)
- APAC StoneBridge Acquisition II Corp: no_revenue (file written, flagged)
- BPAC Blueport Acquisition Ltd: no_revenue (file written, flagged)
- WSTN Westin Acquisition Corp: no_revenue (file written, flagged)
- SCTX Scribe Therapeutics, Inc.: no_revenue (file written, flagged)
- OBX Obsidian Therapeutics, Inc.: no_revenue (file written, flagged)
- BSEM BioStem Technologies, Inc.: no_revenue (file written, flagged)
- DMRC Digimarc Corp: no_revenue (file written, flagged)
- ENHA Enhanced Group Inc.: no_revenue (file written, flagged)
- NUCL Eagle Nuclear Energy Corp.: no_revenue (file written, flagged)
- SWMR Swarmer, Inc: no_revenue (file written, flagged)
- SEV Aptera Motors Corp: no_revenue (file written, flagged)
- AMSS AMASS BRANDS: no_revenue (file written, flagged)
- NUTR NUSATRIP Inc: no_revenue (file written, flagged)
- ADBT Advasa Holdings, Inc.: no_revenue (file written, flagged)
- VIDA VIDA Global Inc.: no_revenue (file written, flagged)
- FBDT First Breach, Inc.: no_revenue (file written, flagged)
- TTRX Turn Therapeutics Inc.: no_revenue (file written, flagged)
- PLYX Polaryx Therapeutics, Inc.: no_revenue (file written, flagged)
- EXYN Exyn Technologies, Inc.: no_revenue (file written, flagged)
- AAC-UN Ares Acquisition Corp III: no_revenue (file written, flagged)
- CNXU Conexeu Sciences Inc.: no_revenue (file written, flagged)
- CURX Curanex Pharmaceuticals Inc: no_revenue (file written, flagged)
- LABT Lakewood-Amedex Biotherapeutics Inc.: no_revenue (file written, flagged)
- CYAB CYABRA, INC.: no_revenue (file written, flagged)
- VOGX Vogenx, Inc.: no_revenue (file written, flagged)
- GYGY Game Your Game Inc.: no_revenue (file written, flagged)
- THEO BOA Acquisition Corp. II: no_revenue (file written, flagged)
- EWAV East West Ave Acquisition Corp.: no_revenue (file written, flagged)
- CAST FreeCast, Inc.: no_revenue (file written, flagged)
- SAMO-UN Samos Energy Acquisition Corp: no_revenue (file written, flagged)
- JONEU Jones Ventures INTL Acquisition1 Corp: no_revenue (file written, flagged)
- MRCO Mercator Acquisition Corp.: no_revenue (file written, flagged)
- RACD Research Alliance Corp IV: no_revenue (file written, flagged)
- BCCQ Bleichroeder Acquisition Corp. III: no_revenue (file written, flagged)
- BREZ Breeze Acquisition Corp. II: no_revenue (file written, flagged)
- OSPRU Osprey Acquisition Corp. III: no_revenue (file written, flagged)
- NCO Southern Cross Acquisition I Corp.: no_revenue (file written, flagged)
- MIACU Meridian3 Industrials Acquisition Corp: no_revenue (file written, flagged)
- AMACU AMR Resources Acquisition Corp.: no_revenue (file written, flagged)
- VII Viking Acquisition Corp. II: no_revenue (file written, flagged)
- BRTMU B&R Technology Merger Corp.: no_revenue (file written, flagged)
- FJDIU ARC Group Securities Acquisition I: no_revenue (file written, flagged)
- FDMM Freedom Metals Acquisition Corp.: no_revenue (file written, flagged)
- TCGX TCGX Acquisition Corp.: no_revenue (file written, flagged)
- MTAKU Market Technology Acquisition Corp: no_revenue (file written, flagged)
- CATLU Catalyst Acquisition Corp.: no_revenue (file written, flagged)
- CCCT Columbus Circle Capital Corp III: no_revenue (file written, flagged)
- TBCVU Thunder Bridge Capital Partners V, Ltd.: no_revenue (file written, flagged)
- SAGU Shreya Acquisition Group: no_revenue (file written, flagged)
- PNAQ-UN Pinnacle Acquisition Corp: no_revenue (file written, flagged)
- SECZ Securitize Corp.: no_revenue (file written, flagged)
- JMKE Jersey Mike's Subs Inc.: no_revenue (file written, flagged)
- FTW PRESIDIO PRODUCTION Co: no_revenue (file written, flagged)
- JBS JBS N.V.: no_revenue (file written, flagged)
- XPRO Expro Ltd: no_revenue (file written, flagged)

## Data flags

- OLED: debt_one_side_only
- ONTO: no_debt_tagged
- ENVA: debt_one_side_only
- RENX: quarter_exceeds_year_capex_2024-12-31
- CLSK: stale_revenue
- META: current_ltd_untagged_2.8B, debt_one_side_only
- TRMK: no_debt_tagged, quarters_off_year_revenue_2023-12-31
- HIVE: debt_one_side_only
- BRK-B: no_debt_tagged, interest_but_no_debt
- JPM: no_capex, debt_one_side_only
- MCW: debt_one_side_only
- ATHS: no_capex, stale_stock_comp, debt_one_side_only
- XOM: stale_shares_diluted, capex_below_segment_2024-12-31
- RPAY: quarter_exceeds_year_capex_2023-12-31
- BAC: no_capex
- CIVB: no_debt_tagged
- PLTR: no_debt_tagged
- PM: stale_stock_comp
- IBM: current_ltd_untagged_6.7B
- GE: debt_too_small_for_interest
- WFC: no_capex
- CRD-A: stale_shares_diluted, capex_below_segment_2023-12-31, capex_below_segment_2025-12-31, capex_below_segment_2024-12-31
- MCFT: no_debt_tagged
- MS: no_capex, debt_one_side_only
- GS: debt_one_side_only
- MCD: debt_one_side_only
- ISRG: no_debt_tagged
- SPCX: no_operating_cash_flow, no_capex, no_revenue
- VZ: stale_capex, stale_stock_comp
- CAT: current_ltd_untagged_7.1B
- DIS: revenue_unverified_2023-09-30, revenue_unverified_2025-09-27, revenue_unverified_2024-09-28
- KLAC: debt_one_side_only
- BLK: debt_one_side_only
- C: stale_stock_comp
- SHOP: no_debt_tagged
- ETN: stale_stock_comp
- PFE: quarters_off_year_revenue_2023-12-31, revenue_unverified_2023-12-31
- DE: debt_one_side_only
- PANW: no_debt_tagged
- MELI: stale_stock_comp
- CB: no_capex, stale_stock_comp
- VRTX: no_debt_tagged
- TMUS: debt_one_side_only, debt_too_small_for_interest
- CRWD: debt_one_side_only
- BX: current_ltd_untagged_0.7B, debt_one_side_only
- ANET: no_debt_tagged
- AMT: quarters_off_year_capex_2025-12-31, v2 quarterly capex not used: its quarters did not add up to the year
- APP: stale_capex, quarters_off_year_revenue_2024-12-31, debt_one_side_only
- WELL: revenue_unverified_2025-12-31, current_ltd_untagged_3.0B, debt_one_side_only
- SO: stale_stock_comp
- CME: debt_one_side_only
- ENB: no_operating_cash_flow, no_capex, reports_in_CAD
- PLD: current_ltd_untagged_2.0B, debt_one_side_only
- MCK: quarters_off_year_capex_2024-03-31, quarters_off_year_capex_2025-03-31, capex_below_segment_2026-03-31
- DUK: revenue_unverified_2023-12-31, revenue_unverified_2025-12-31
- KKR: stale_capex, no_debt_tagged, interest_but_no_debt
- DASH: no_debt_tagged
- CI: stale_capex
- CDNS: debt_one_side_only
- EQIX: quarters_off_year_revenue_2023-12-31
- RSG: stale_stock_comp
- AON: capex_below_segment_2023-12-31, capex_below_segment_2025-12-31, capex_below_segment_2024-12-31
- COIN: stale_capex
- SNOW: no_debt_tagged
- PNC: no_capex, stale_stock_comp, debt_one_side_only
- CP: no_operating_cash_flow, no_capex, reports_in_CAD
- HOOD: stale_capex, no_debt_tagged
- USB: no_capex, debt_one_side_only
- ZTS: current_ltd_untagged_0.8B
- APD: stale_operating_cash_flow, debt_one_side_only
- BDX: quarters_off_year_revenue_2025-09-30, v2 quarterly revenue not used: its quarters did not add up to the year
- VST: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31
- NEM: debt_one_side_only
- CMG: no_debt_tagged, debt_one_side_only
- ORLY: debt_one_side_only
- ROP: stale_capex
- TRV: no_capex
- SNPS: quarters_off_year_revenue_2023-10-31
- APO: no_capex, debt_one_side_only
- AZO: debt_one_side_only
- KMI: stale_stock_comp
- MNST: no_debt_tagged
- ABNB: stale_capex
- AEP: quarters_off_year_capex_2023-12-31
- AFL: no_capex
- TFC: stale_capex
- REGN: debt_one_side_only
- MET: no_capex
- ALL: debt_one_side_only
- JCI: quarters_off_year_operating_cash_flow_2024-09-30
- SPG: debt_one_side_only
- CPRT: no_debt_tagged
- MPC: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31
- AMP: no_debt_tagged
- PCAR: no_debt_tagged, quarters_off_year_capex_2023-12-31, quarters_off_year_capex_2024-12-31, interest_but_no_debt
- EA: debt_one_side_only
- AIG: stale_capex, debt_one_side_only
- TTWO: stale_shares_diluted
- EW: debt_one_side_only
- SLB: debt_one_side_only
- CCI: quarter_exceeds_year_capex_2023-12-31
- PSKY: stale_revenue, stale_net_income, stale_operating_cash_flow, stale_capex, stale_stock_comp, stale_fcf
- PSA: current_ltd_untagged_1.2B
- EXC: stale_stock_comp
- MSCI: debt_one_side_only
- DDOG: no_debt_tagged
- FERG: stale_revenue, stale_net_income, stale_operating_cash_flow, stale_capex, stale_stock_comp, stale_fcf
- ALNY: no_debt_tagged, interest_but_no_debt
- VEEV: stale_capex, no_debt_tagged
- FIS: quarters_off_year_capex_2023-12-31, capex_below_segment_2025-12-31, capex_below_segment_2024-12-31
- F: no_debt_tagged, interest_but_no_debt
- AME: capex_below_segment_2023-12-31
- VLO: stale_capex
- OXY: quarters_off_year_revenue_2025-12-31, v2 quarterly revenue not used: its quarters did not add up to the year
- SNDK: no_debt_tagged
- PRU: no_capex
- BKR: stale_shares_diluted
- CRCL: no_debt_tagged, revenue_unverified_2025-12-31, revenue_unverified_2023-12-31, revenue_unverified_2024-12-31
- ETR: stale_stock_comp
- TRGP: quarters_off_year_revenue_2024-12-31, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, debt_one_side_only
- ED: debt_one_side_only, debt_too_small_for_interest
- HIG: debt_one_side_only
- PAYX: debt_one_side_only
- NET: no_debt_tagged
- VICI: current_ltd_untagged_1.5B, debt_one_side_only
- GRMN: no_debt_tagged
- DXCM: no_debt_tagged
- CSGP: debt_one_side_only
- ACGL: debt_one_side_only
- FWONA: stale_shares_diluted, quarters_off_year_operating_cash_flow_2024-12-31, capex_below_segment_2023-12-31
- TTD: no_debt_tagged
- EXR: quarters_off_year_capex_2025-12-31, revenue_unverified_2024-12-31, revenue_unverified_2025-12-31, v2 quarterly capex not used: its quarters did not add up to the year
- STT: stale_stock_comp, debt_one_side_only
- CRDO: no_debt_tagged
- LPLA: debt_one_side_only
- MTB: stale_capex
- ROK: stale_capex
- MLM: capex_below_segment_2024-12-31
- VTR: quarters_off_year_capex_2023-12-31, quarters_off_year_capex_2024-12-31, quarters_off_year_capex_2025-12-31, current_ltd_untagged_0.7B, v2 quarterly capex not used: its quarters did not add up to the year
- HUBS: no_debt_tagged
- RJF: no_debt_tagged
- TEAM: debt_one_side_only
- DTE: stale_stock_comp
- FANG: stale_stock_comp
- GIS: revenue_unverified_2024-05-26
- PPL: revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, revenue_unverified_2024-12-31
- DOV: quarters_off_year_revenue_2023-12-31, quarters_off_year_operating_cash_flow_2024-12-31
- MKL: quarters_off_year_revenue_2024-12-31, debt_one_side_only
- SYF: no_capex, debt_one_side_only
- MPWR: no_debt_tagged
- HSY: stale_shares_diluted
- LEN: debt_one_side_only
- ATO: stale_stock_comp
- NTRS: no_debt_tagged
- TDY: stale_stock_comp
- IBKR: no_capex, debt_one_side_only
- SUNB: no_capex
- FE: stale_stock_comp
- BAM: quarter_exceeds_year_capex_2024-12-31, quarters_off_year_capex_2024-12-31, revenue_unverified_2025-12-31, revenue_unverified_2023-12-31, revenue_unverified_2024-12-31, debt_one_side_only
- TOST: no_debt_tagged
- CINF: stale_stock_comp, debt_one_side_only
- WSM: no_debt_tagged
- FOXA: debt_one_side_only
- TSCO: debt_one_side_only
- DLTR: quarters_off_year_operating_cash_flow_2025-02-01
- NTRA: debt_one_side_only
- RDDT: no_debt_tagged
- INSM: debt_one_side_only
- TROW: no_debt_tagged
- AFRM: current_ltd_untagged_0.2B, debt_one_side_only
- CHSCP: quarters_off_year_revenue_2025-08-31, v2 quarterly revenue not used: its quarters did not add up to the year
- CMS: stale_capex
- RF: no_capex
- NVR: no_debt_tagged
- DVN: revenue_unverified_2025-12-31
- INVH: revenue_unverified_2024-12-31, revenue_unverified_2025-12-31, current_ltd_untagged_1.0B, debt_one_side_only
- SOFI: no_debt_tagged
- TPL: stale_capex, no_debt_tagged
- ZM: no_debt_tagged
- EXE: debt_one_side_only
- HONA: no_operating_cash_flow, no_capex, no_revenue
- GPN: quarters_off_year_revenue_2024-12-31
- CFG: stale_capex
- MDB: no_debt_tagged
- DKNG: current_ltd_untagged_0.0B, debt_one_side_only
- IFF: quarters_off_year_revenue_2025-12-31, v2 quarterly revenue not used: its quarters did not add up to the year
- DOW: quarters_off_year_capex_2023-12-31
- TWLO: stale_capex, debt_one_side_only
- PINS: no_debt_tagged
- WY: debt_one_side_only
- ZS: no_debt_tagged
- AVAV: debt_one_side_only
- ESS: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, current_ltd_untagged_0.4B, debt_one_side_only
- LULU: no_debt_tagged, debt_one_side_only
- TSN: stale_stock_comp
- EME: stale_stock_comp, no_debt_tagged
- FN: no_debt_tagged
- P: no_debt_tagged, debt_one_side_only
- EQH: no_capex
- TW: no_debt_tagged
- ULTA: debt_one_side_only
- RPRX: no_capex
- PKG: debt_one_side_only
- PNR: current_ltd_untagged_0.0B, debt_one_side_only
- YUMC: debt_one_side_only
- RS: debt_one_side_only
- OKTA: no_debt_tagged
- BAX: debt_one_side_only, debt_too_small_for_interest
- MOH: debt_one_side_only
- SNA: revenue_unverified_2024-12-28, revenue_unverified_2026-01-03, revenue_unverified_2023-12-30
- LOGI: no_debt_tagged
- SFM: no_debt_tagged
- SUI: quarters_off_year_revenue_2023-12-31, quarters_off_year_revenue_2025-12-31, v2 quarterly revenue not used: its quarters did not add up to the year
- CRS: debt_one_side_only
- WSO: debt_one_side_only
- NWSA: quarters_off_year_revenue_2024-06-30, quarters_off_year_operating_cash_flow_2025-06-30
- ARCC: no_capex, debt_one_side_only, no_revenue
- EXPD: debt_one_side_only
- FFIV: no_debt_tagged
- HAL: stale_stock_comp
- SMCI: current_ltd_untagged_2.0B
- DOCU: no_debt_tagged
- ZG: no_debt_tagged
- RKLB: debt_one_side_only
- LYB: stale_shares_diluted
- CF: debt_one_side_only
- APTV: quarters_off_year_revenue_2025-12-31
- DECK: no_debt_tagged
- DT: no_debt_tagged
- J: debt_one_side_only
- TXT: no_debt_tagged, interest_but_no_debt
- EG: no_capex
- RIVN: debt_one_side_only
- GGG: debt_one_side_only
- UNM: debt_one_side_only
- FNF: debt_one_side_only
- EWBC: stale_capex, debt_one_side_only
- QXO: debt_one_side_only
- WPC: stale_capex, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, current_ltd_untagged_0.6B, debt_one_side_only
- CG: no_debt_tagged, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, interest_but_no_debt
- DUOL: no_debt_tagged
- TLN: capex_below_segment_2024-12-31, capex_below_segment_2025-12-31, revenue_unverified_2022-12-31, revenue_unverified_2024-12-31, revenue_unverified_2025-12-31
- RBRK: no_debt_tagged, debt_one_side_only
- BWXT: debt_one_side_only
- ALAB: no_debt_tagged
- RGA: stale_capex, debt_one_side_only
- SOLV: revenue_unverified_2025-12-31, revenue_unverified_2023-12-31, revenue_unverified_2024-12-31
- JKHY: debt_one_side_only
- MBGL: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- REG: stale_shares_diluted, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, current_ltd_untagged_0.8B, debt_one_side_only
- TER: no_debt_tagged, debt_one_side_only
- GLPI: quarter_exceeds_year_capex_2024-12-31, current_ltd_untagged_0.0B, debt_one_side_only, v2 quarterly capex not used: its quarters did not add up to the year
- IOT: no_debt_tagged
- TXRH: debt_one_side_only
- OWL: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, debt_one_side_only
- ARE: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, debt_one_side_only
- THC: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31
- LBRDK: stale_revenue, stale_capex, quarters_off_year_operating_cash_flow_2025-12-31
- CLBK: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- NLY: no_capex, stale_stock_comp, no_debt_tagged, no_revenue, interest_but_no_debt
- JLL: stale_capex
- ALLY: no_capex, stale_stock_comp, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, debt_too_small_for_interest
- DD: quarters_off_year_operating_cash_flow_2023-12-31, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31
- CPT: quarter_exceeds_year_capex_2023-12-31, quarters_off_year_capex_2023-12-31, quarter_exceeds_year_capex_2024-12-31, quarters_off_year_capex_2024-12-31, quarter_exceeds_year_capex_2025-12-31, quarters_off_year_capex_2025-12-31, current_ltd_untagged_1.2B, v2 quarterly capex not used: its quarters did not add up to the year
- RL: stale_capex
- MAA: current_ltd_untagged_1.6B
- PAYC: debt_one_side_only
- MANH: no_debt_tagged
- ELS: quarters_off_year_capex_2023-12-31
- RGLD: no_capex, debt_one_side_only
- AR: capex_below_segment_2025-12-31
- AMH: debt_one_side_only
- ASTS: quarters_off_year_revenue_2024-12-31, revenue_unverified_2024-12-31
- NVT: quarters_off_year_revenue_2023-12-31
- CBRS: no_operating_cash_flow, no_capex, no_revenue
- CNH: no_capex, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31
- IONQ: no_debt_tagged
- CHRW: debt_one_side_only
- RNR: no_capex, debt_one_side_only
- LECO: debt_one_side_only
- UTHR: no_debt_tagged
- INCY: stale_capex, no_debt_tagged
- HLI: no_debt_tagged
- AKAM: no_debt_tagged
- ALGN: no_debt_tagged
- TEM: no_debt_tagged, interest_but_no_debt
- DTM: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, debt_one_side_only
- SF: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, debt_one_side_only, debt_too_small_for_interest
- NXT: no_debt_tagged
- OHI: revenue_unverified_2023-12-31, debt_one_side_only
- FHN: debt_one_side_only
- BXP: revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, revenue_unverified_2024-12-31
- SJM: stale_shares_diluted
- PR: debt_one_side_only
- HST: capex_below_segment_2024-12-31, capex_below_segment_2023-12-31, capex_below_segment_2025-12-31
- NTNX: no_debt_tagged
- WTRG: stale_capex
- HIMS: no_debt_tagged
- KNSL: debt_one_side_only
- EXAS: no_debt_tagged
- MRNA: debt_one_side_only
- DOCS: no_debt_tagged
- ROIV: no_debt_tagged, quarters_off_year_revenue_2024-03-31
- WING: debt_one_side_only
- ROKU: no_debt_tagged
- PEN: no_debt_tagged
- CUBE: no_debt_tagged, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, interest_but_no_debt
- RRC: stale_stock_comp, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, revenue_unverified_2024-12-31, debt_one_side_only
- EPAM: debt_one_side_only
- NBIX: no_debt_tagged
- AIT: debt_one_side_only
- HII: debt_one_side_only
- DOC: quarters_off_year_capex_2023-12-31, quarters_off_year_capex_2024-12-31, quarters_off_year_capex_2025-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, revenue_unverified_2024-12-31, current_ltd_untagged_1.4B, debt_one_side_only, v2 quarterly capex not used: its quarters did not add up to the year
- EXEL: no_debt_tagged
- ESTC: debt_one_side_only
- BRBR: debt_one_side_only
- ARMK: stale_operating_cash_flow
- CR: quarters_off_year_operating_cash_flow_2023-12-31
- SSB: no_debt_tagged
- CAVA: no_debt_tagged
- WBS: debt_one_side_only
- TECH: debt_one_side_only
- SCCO: debt_one_side_only
- NYT: no_debt_tagged
- U: no_debt_tagged
- GME: debt_one_side_only
- AFG: no_capex, debt_one_side_only
- ARX: no_capex, debt_one_side_only
- OGE: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31
- AYI: debt_one_side_only
- PRI: stale_capex
- ORI: no_capex
- EGP: current_ltd_untagged_0.2B, debt_one_side_only
- CRBG: no_capex, debt_one_side_only, debt_too_small_for_interest
- ERIE: no_debt_tagged
- MLI: capex_below_segment_2024-12-28, debt_one_side_only
- AGNC: no_capex, stale_revenue, no_debt_tagged
- ALV: stale_stock_comp
- RYAN: quarters_off_year_capex_2023-12-31
- FRBT: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- PNFP: no_debt_tagged
- REXR: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, current_ltd_untagged_1.0B, debt_one_side_only
- WAL: no_capex
- MAIR: no_operating_cash_flow, no_capex, no_revenue
- CHYM: no_debt_tagged
- ONB: no_debt_tagged
- APPF: no_debt_tagged
- WTFC: no_debt_tagged
- PCOR: no_debt_tagged
- FRT: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, v2 quarterly capex not used: its quarters did not add up to the year
- CFR: no_debt_tagged
- FLR: debt_one_side_only
- CVLT: no_debt_tagged
- JEF: quarter_exceeds_year_capex_2023-11-30, revenue_unverified_2024-11-30, revenue_unverified_2025-11-30, revenue_unverified_2023-11-30
- AXS: no_capex
- LOAR: no_capex
- NNN: no_capex, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31
- BRX: current_ltd_untagged_0.4B, debt_one_side_only
- QRVO: debt_one_side_only
- CBSH: no_debt_tagged
- PSN: debt_one_side_only
- DINO: debt_one_side_only
- TTEK: debt_one_side_only
- UMBF: debt_one_side_only
- ZION: debt_one_side_only
- BPOP: debt_one_side_only
- AES: no_debt_tagged, interest_but_no_debt
- GMRS: no_operating_cash_flow, no_capex, no_revenue
- GWRE: current_ltd_untagged_0.0B, debt_one_side_only
- OBDC: no_capex, current_ltd_untagged_1.8B, debt_one_side_only, no_revenue
- BBIO: current_ltd_untagged_0.6B, debt_one_side_only
- MKTX: debt_one_side_only
- FIVE: no_debt_tagged
- BMI: no_debt_tagged, debt_one_side_only
- TPG: no_capex, debt_one_side_only
- VG: quarters_off_year_capex_2024-12-31
- KNX: stale_capex, debt_too_small_for_interest
- UGI: stale_stock_comp
- CHE: debt_one_side_only
- ARXS: no_operating_cash_flow, no_capex, no_revenue
- MEDP: no_debt_tagged
- OKLO: debt_one_side_only, no_revenue
- BXSL: no_capex, debt_one_side_only, no_revenue
- OTF: no_capex, debt_one_side_only, no_revenue
- APLD: quarters_off_year_revenue_2024-05-31, quarters_off_year_revenue_2025-05-31, capex_below_segment_2024-05-31
- CART: no_debt_tagged
- VNO: revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, revenue_unverified_2024-12-31
- SLM: no_capex
- VOYA: stale_capex
- STAG: debt_one_side_only
- OMF: no_capex, current_ltd_untagged_0.8B, debt_one_side_only
- RVMD: no_debt_tagged
- WTS: debt_one_side_only
- OCTV: no_operating_cash_flow, no_capex, no_revenue
- LNC: no_capex
- GMED: no_debt_tagged, debt_one_side_only
- PCTY: debt_one_side_only
- APA: capex_below_segment_2024-12-31, no_revenue
- KTOS: no_debt_tagged, debt_one_side_only
- ACHR: short_history
- COKE: stale_stock_comp, stale_shares_diluted
- PB: no_debt_tagged
- STWD: capex_below_segment_2025-12-31, capex_below_segment_2023-12-31, capex_below_segment_2024-12-31, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31
- AM: debt_one_side_only
- GTLB: no_debt_tagged
- FR: no_capex, current_ltd_untagged_0.0B
- KEX: debt_one_side_only
- R: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31
- LYFT: no_capex
- EPRT: stale_capex, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, current_ltd_untagged_0.4B, debt_one_side_only
- IDA: stale_stock_comp
- GPK: stale_capex
- GH: debt_one_side_only
- QVCG: debt_too_small_for_interest
- JBTM: quarters_off_year_operating_cash_flow_2023-12-31
- FBIN: debt_one_side_only
- CORT: no_debt_tagged
- KBR: stale_stock_comp
- CTRE: stale_capex, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, debt_one_side_only
- BTGO: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- TTAN: no_debt_tagged
- CSQR: no_operating_cash_flow, no_capex, current_ltd_untagged_1.0B, debt_one_side_only, no_revenue
- RGEN: debt_one_side_only
- ZWS: stale_capex
- RITM: no_capex, revenue_unverified_2024-12-31, current_ltd_untagged_5.0B, debt_one_side_only
- AHR: no_debt_tagged, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, interest_but_no_debt, v2 quarterly capex not used: its quarters did not add up to the year
- TMHC: debt_one_side_only
- ENSG: stale_capex
- GKOS: no_debt_tagged
- BEN: debt_one_side_only
- LPX: debt_one_side_only
- QTWO: no_debt_tagged
- MGM: debt_one_side_only
- TREX: no_debt_tagged
- FSK: no_capex, debt_one_side_only, no_revenue
- INIO: no_operating_cash_flow, no_capex, no_revenue
- AUR: no_debt_tagged
- ALK: capex_below_segment_2024-12-31, capex_below_segment_2025-12-31
- IVZ: debt_one_side_only
- MARA: revenue_unverified_2025-12-31
- TRNO: current_ltd_untagged_0.1B
- JOBY: debt_one_side_only
- H: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31
- CDE: debt_one_side_only, debt_too_small_for_interest
- AN: debt_one_side_only, debt_too_small_for_interest
- MDGL: quarter_exceeds_year_capex_2025-12-31, current_ltd_untagged_0.0B, debt_one_side_only
- VRNS: no_debt_tagged
- STUB: debt_one_side_only
- CHRD: debt_one_side_only
- HR: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, debt_one_side_only
- MTDR: debt_one_side_only
- RLI: stale_stock_comp, debt_one_side_only
- HLNE: debt_one_side_only
- AMG: debt_one_side_only
- GATX: stale_capex, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31
- MMSI: debt_one_side_only
- VGNT: no_operating_cash_flow, no_capex, no_revenue
- SWX: quarters_off_year_revenue_2024-12-31
- SMR: no_debt_tagged
- CGNX: no_debt_tagged
- HOMB: debt_one_side_only
- FCFS: debt_one_side_only
- UDR: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, current_ltd_untagged_0.3B, debt_one_side_only
- RMBS: no_debt_tagged
- SPSC: no_debt_tagged
- LOPE: no_debt_tagged
- W: debt_one_side_only
- SHAK: debt_one_side_only
- BCPC: stale_capex, debt_one_side_only
- STEP: debt_one_side_only
- S: no_debt_tagged
- ADC: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, current_ltd_untagged_0.1B
- ORA: debt_one_side_only, debt_too_small_for_interest
- GBCI: no_debt_tagged
- MAIN: no_capex, debt_one_side_only, no_revenue
- UHAL: stale_shares_diluted, current_ltd_untagged_0.9B, debt_one_side_only
- CUZ: debt_one_side_only
- CRUS: no_debt_tagged
- VLY: debt_one_side_only
- PEGA: no_debt_tagged
- SLAB: no_debt_tagged
- SAIC: revenue_unverified_2025-01-31, revenue_unverified_2024-02-02
- VNOM: no_capex, debt_one_side_only
- UBSI: debt_one_side_only
- AAON: stale_capex, no_debt_tagged, debt_one_side_only
- FFIN: debt_one_side_only
- KRG: debt_one_side_only
- ETSY: quarters_off_year_revenue_2025-12-31
- IRTC: no_debt_tagged
- NJR: stale_capex, stale_stock_comp
- LIF: no_debt_tagged
- URBN: no_debt_tagged
- GNTX: debt_one_side_only
- CROX: debt_one_side_only
- PATH: no_debt_tagged
- BILL: debt_one_side_only
- KVYO: no_debt_tagged
- LSTR: no_debt_tagged, debt_one_side_only
- PIPR: stale_capex, quarters_off_year_revenue_2023-12-31, quarters_off_year_revenue_2025-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, debt_one_side_only, v2 quarterly revenue not used: its quarters did not add up to the year
- SITM: no_debt_tagged
- MMED: no_debt_tagged
- JAN: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- MTH: stale_revenue
- JXN: no_capex, current_ltd_untagged_0.6B, debt_one_side_only
- ABG: capex_below_segment_2024-12-31, v2 quarterly capex not used: its quarters did not add up to the year
- ADIG: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- KNF: capex_below_segment_2024-12-31
- MC: no_debt_tagged, no_revenue
- NEU: stale_stock_comp, debt_one_side_only
- ULS: debt_one_side_only
- MRCY: no_debt_tagged
- WMG: stale_stock_comp, stale_shares_diluted, debt_one_side_only
- BOX: debt_one_side_only
- OSCR: debt_one_side_only
- LAZ: debt_one_side_only
- HXL: debt_one_side_only
- WTM: no_capex, debt_one_side_only
- EPR: quarters_off_year_capex_2023-12-31, quarters_off_year_capex_2024-12-31, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, debt_one_side_only
- SR: stale_stock_comp
- VEEE: debt_one_side_only
- FROG: no_debt_tagged
- SBRA: no_capex, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, current_ltd_untagged_0.4B, debt_one_side_only
- PECO: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, debt_one_side_only
- AUB: no_capex
- BYD: debt_one_side_only
- ST: debt_one_side_only
- ACA: quarters_off_year_revenue_2025-12-31, v2 quarterly revenue not used: its quarters did not add up to the year
- HRI: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31
- ADT: stale_shares_diluted
- AROC: debt_one_side_only
- CORZ: debt_one_side_only
- IRT: current_ltd_untagged_0.1B, debt_one_side_only
- ABCB: no_debt_tagged
- VIAV: debt_one_side_only
- ANF: no_debt_tagged
- IBOC: no_debt_tagged
- KMPR: debt_one_side_only
- MAC: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, debt_one_side_only
- CRSP: debt_one_side_only
- COLD: no_debt_tagged, interest_but_no_debt
- TENB: no_debt_tagged
- MGY: debt_one_side_only
- ESE: quarters_off_year_revenue_2024-09-30
- KRC: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31
- RHI: stale_stock_comp, no_debt_tagged
- PLMR: debt_one_side_only
- CSW: stale_stock_comp
- GAP: debt_one_side_only
- ASB: no_capex, stale_stock_comp
- AGO: no_capex, stale_stock_comp, debt_one_side_only
- SFBS: stale_capex, no_debt_tagged
- HL: quarters_off_year_revenue_2025-12-31, debt_one_side_only, v2 quarterly revenue not used: its quarters did not add up to the year
- BOOT: no_debt_tagged
- GBDC: no_capex, debt_one_side_only, no_revenue
- SLG: stale_capex, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, current_ltd_untagged_1.4B
- PJT: no_debt_tagged
- BE: stale_stock_comp
- VSAT: stale_capex
- CALM: no_debt_tagged
- RGTI: no_debt_tagged
- CRC: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, debt_one_side_only
- INSP: no_debt_tagged
- ZLAB: debt_one_side_only
- MRP: no_capex, short_history
- BGC: stale_stock_comp, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31
- QLYS: no_debt_tagged
- PCVX: no_debt_tagged, no_revenue
- CLF: debt_one_side_only
- BRC: debt_one_side_only
- BWIN: debt_one_side_only
- COLB: stale_capex, no_debt_tagged
- KTB: quarters_off_year_revenue_2026-01-03, v2 quarterly revenue not used: its quarters did not add up to the year
- HGV: quarters_off_year_revenue_2023-12-31, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, debt_one_side_only
- NUVL: no_capex, no_debt_tagged, no_revenue
- CNO: no_capex
- GLXY: quarters_off_year_revenue_2024-12-31
- SOUN: no_debt_tagged
- TCBI: debt_one_side_only
- HWKN: debt_one_side_only
- FRVO: no_operating_cash_flow, no_capex, no_revenue
- KBH: no_debt_tagged
- KRYS: no_debt_tagged
- WK: no_debt_tagged
- VCTR: debt_one_side_only
- SMPL: debt_one_side_only
- MATX: quarters_off_year_capex_2023-12-31
- DDS: stale_stock_comp, debt_one_side_only
- CHH: quarters_off_year_capex_2023-12-31, debt_one_side_only
- LSCC: no_debt_tagged
- AX: debt_one_side_only
- RYN: quarters_off_year_capex_2023-12-31, quarters_off_year_capex_2025-12-31
- FCBM: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- PLXS: no_debt_tagged
- NE: debt_one_side_only
- CNK: stale_operating_cash_flow, stale_capex, no_debt_tagged, interest_but_no_debt
- RARE: no_debt_tagged
- SKT: no_operating_cash_flow, no_capex, debt_one_side_only
- AZZ: debt_one_side_only
- M: revenue_unverified_2024-02-03, revenue_unverified_2025-02-01, revenue_unverified_2026-01-31
- TNL: current_ltd_untagged_0.7B, debt_one_side_only
- HIW: no_debt_tagged, interest_but_no_debt
- FHI: quarter_exceeds_year_capex_2024-12-31, debt_one_side_only
- HASI: stale_capex, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31
- FRPT: no_debt_tagged
- HTGC: debt_one_side_only, no_revenue
- AVPT: no_debt_tagged
- BL: no_debt_tagged
- FBP: debt_one_side_only
- QNT: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- FRHC: debt_too_small_for_interest
- AIR: debt_one_side_only
- FULT: no_capex, debt_one_side_only
- FLG: stale_capex
- BXMT: no_debt_tagged, quarter_exceeds_year_revenue_2024-12-31, v2 quarterly revenue not used: its quarters did not add up to the year
- ZETA: current_ltd_untagged_0.0B, debt_one_side_only
- BCC: debt_one_side_only
- PRCT: debt_one_side_only
- UNF: no_debt_tagged
- SEZL: no_debt_tagged
- COMP: debt_one_side_only
- FHB: no_debt_tagged, debt_one_side_only
- GNW: no_capex, debt_one_side_only
- APAM: debt_one_side_only
- DBX: no_debt_tagged
- PAG: quarters_off_year_capex_2025-12-31
- FRSH: no_debt_tagged
- AVA: debt_one_side_only, debt_too_small_for_interest
- WSFS: no_debt_tagged
- GFF: quarters_off_year_revenue_2025-09-30, v2 quarterly revenue not used: its quarters did not add up to the year
- SIG: no_debt_tagged
- DAVE: no_debt_tagged, debt_one_side_only
- FIGR: no_capex, current_ltd_untagged_0.1B, debt_one_side_only
- FUL: debt_one_side_only
- CATY: debt_one_side_only
- EXPO: no_debt_tagged
- TDS: quarter_exceeds_year_revenue_2023-12-31, quarters_off_year_revenue_2024-12-31
- QS: no_debt_tagged, no_revenue
- BHF: no_capex, debt_one_side_only
- BNL: current_ltd_untagged_0.4B, debt_one_side_only
- DLB: no_debt_tagged
- WHD: stale_shares_diluted, no_debt_tagged, debt_one_side_only
- CBU: no_debt_tagged, quarters_off_year_revenue_2023-12-31
- VKTX: no_capex, no_debt_tagged
- UEC: no_debt_tagged, capex_below_segment_2024-07-31, capex_below_segment_2023-07-31, capex_below_segment_2025-07-31
- CVCO: current_ltd_untagged_0.0B
- ALH: no_debt_tagged, interest_but_no_debt
- WSBC: debt_one_side_only
- KFY: debt_one_side_only
- AWR: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, debt_one_side_only
- CAKE: debt_one_side_only
- MHO: no_debt_tagged
- NHI: quarters_off_year_capex_2023-12-31, quarters_off_year_capex_2024-12-31, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, v2 quarterly capex not used: its quarters did not add up to the year
- PTGX: no_debt_tagged
- EBC: no_debt_tagged
- PFSI: debt_one_side_only
- LMND: no_debt_tagged
- CACC: debt_one_side_only, debt_too_small_for_interest
- BUR: debt_one_side_only
- SNEX: debt_too_small_for_interest
- CAR: no_capex
- AGX: no_debt_tagged
- BDC: debt_one_side_only
- CWEN: stale_stock_comp
- PAR: quarters_off_year_revenue_2023-12-31
- AVBC: no_debt_tagged
- FCPT: stale_capex, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, current_ltd_untagged_0.2B, debt_one_side_only
- PPLI: quarters_off_year_revenue_2025-12-31, v2 quarterly revenue not used: its quarters did not add up to the year
- NMIH: no_debt_tagged
- PBAM: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- BFH: stale_capex, debt_one_side_only
- NOG: debt_one_side_only
- BRZE: no_debt_tagged
- CRNX: no_debt_tagged
- ACVA: no_debt_tagged
- SXI: stale_stock_comp, debt_one_side_only
- INDB: debt_one_side_only
- BKU: stale_capex, debt_one_side_only
- BOH: debt_one_side_only
- BANF: debt_one_side_only
- PRK: debt_one_side_only
- FIBK: no_capex, current_ltd_untagged_0.0B
- CDP: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, current_ltd_untagged_0.1B, debt_one_side_only
- SRRK: debt_one_side_only
- MPT: current_ltd_untagged_1.6B, debt_one_side_only, v2 quarterly capex not used: its quarters did not add up to the year
- YOU: no_debt_tagged
- APLE: quarters_off_year_capex_2023-12-31, current_ltd_untagged_0.3B, debt_one_side_only
- SSRM: no_debt_tagged, debt_one_side_only
- CVBF: no_debt_tagged
- VERX: stale_capex, debt_one_side_only
- QUBT: no_debt_tagged
- TBBK: debt_one_side_only
- CPRX: no_debt_tagged
- VAL: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, debt_one_side_only, debt_too_small_for_interest
- BOKF: current_ltd_untagged_4.2B, debt_one_side_only
- TGTX: debt_one_side_only
- VC: stale_capex
- PBF: debt_one_side_only
- INTA: no_debt_tagged
- UE: no_debt_tagged, revenue_unverified_2023-12-31, interest_but_no_debt
- NVST: debt_one_side_only
- SMMT: stale_revenue, no_debt_tagged
- AKR: current_ltd_untagged_0.1B, debt_one_side_only
- COSO: no_debt_tagged
- DEI: debt_one_side_only
- XENE: no_debt_tagged
- SBCF: no_capex, debt_one_side_only
- ALKT: no_debt_tagged
- IPAR: capex_below_segment_2024-12-31, capex_below_segment_2023-12-31, capex_below_segment_2025-12-31
- LXP: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, debt_one_side_only
- MUR: capex_below_segment_2023-12-31, capex_below_segment_2025-12-31, capex_below_segment_2024-12-31
- FIG: no_debt_tagged
- SFNC: quarter_exceeds_year_revenue_2025-12-31, current_ltd_untagged_0.0B, debt_one_side_only
- UI: no_debt_tagged, debt_one_side_only
- PSMT: quarters_off_year_operating_cash_flow_2023-08-31
- AGYS: no_debt_tagged, debt_one_side_only
- TWST: no_debt_tagged
- POWI: no_debt_tagged
- PTEN: debt_one_side_only
- ACAD: no_debt_tagged
- BB: quarters_off_year_revenue_2024-02-29, debt_one_side_only
- MQ: no_debt_tagged
- KYMR: no_debt_tagged
- WAFD: no_debt_tagged
- XE: no_operating_cash_flow, no_capex, no_debt_tagged, debt_one_side_only, no_revenue
- SYBT: debt_one_side_only
- CRVL: no_debt_tagged
- CRK: debt_one_side_only
- FRME: no_capex, no_debt_tagged
- TNET: debt_one_side_only
- CCOI: debt_one_side_only
- CURB: debt_one_side_only
- AMBA: no_debt_tagged
- HHH: current_ltd_untagged_0.7B, debt_one_side_only
- BANR: no_debt_tagged, no_revenue, interest_but_no_debt
- VAC: capex_below_segment_2024-12-31, capex_below_segment_2023-12-31, capex_below_segment_2025-12-31, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, current_ltd_untagged_0.6B
- ACLS: no_debt_tagged
- WRBY: no_debt_tagged
- TSLX: no_capex, debt_one_side_only, no_revenue
- PFS: quarter_exceeds_year_capex_2024-12-31, debt_one_side_only
- MWH: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- NBTB: debt_one_side_only
- RKT: quarters_off_year_revenue_2025-12-31
- CALX: no_debt_tagged
- TDC: no_debt_tagged
- VCEL: no_debt_tagged
- EFOR: debt_one_side_only
- NSP: debt_one_side_only
- SPNT: no_capex, debt_one_side_only
- CNS: no_debt_tagged
- IVT: current_ltd_untagged_0.0B, debt_one_side_only
- MSGE: no_capex, revenue_unverified_2025-06-30, revenue_unverified_2024-06-30
- YSS: no_operating_cash_flow, no_capex, no_revenue
- YSWY: no_operating_cash_flow, no_capex, no_revenue
- LFTO: no_operating_cash_flow, no_capex, no_revenue
- ADUS: debt_one_side_only
- OSW: debt_one_side_only
- DV: no_debt_tagged
- VOYG: no_debt_tagged, debt_one_side_only
- PAYO: no_debt_tagged
- LLYVA: no_capex
- PK: current_ltd_untagged_0.2B, debt_one_side_only
- SM: quarter_exceeds_year_capex_2023-12-31, quarters_off_year_capex_2023-12-31
- EFSC: no_debt_tagged
- SMA: stale_capex, stale_shares_diluted, current_ltd_untagged_0.0B, debt_one_side_only
- OII: debt_one_side_only
- STRA: no_debt_tagged
- CBC: no_debt_tagged
- ABR: no_capex, current_ltd_untagged_5.1B, debt_one_side_only
- LRN: debt_one_side_only
- TGLS: stale_stock_comp
- NNI: stale_revenue, quarter_exceeds_year_capex_2024-12-31, debt_one_side_only
- KNTK: quarters_off_year_capex_2023-12-31
- JJSF: debt_one_side_only
- BXDC: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- BOBS: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- OFG: no_debt_tagged
- AGIO: no_debt_tagged
- TRIP: quarters_off_year_revenue_2025-12-31
- AAP: debt_one_side_only
- BANC: stale_stock_comp, quarter_exceeds_year_revenue_2023-12-31, debt_one_side_only
- PGNY: no_debt_tagged
- DBRG: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, debt_one_side_only
- GRAL: no_debt_tagged
- KGS: current_ltd_untagged_0.0B, debt_one_side_only
- PCT: no_debt_tagged, interest_but_no_debt, short_history
- DPC: no_operating_cash_flow, no_capex, no_revenue
- BCRX: debt_one_side_only
- PRM: debt_one_side_only
- PLUS: no_debt_tagged, quarters_off_year_capex_2024-03-31, quarters_off_year_capex_2025-03-31
- MBLY: no_debt_tagged
- LEVI: debt_one_side_only
- UFPT: stale_capex
- PS: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- LMRI: no_operating_cash_flow, no_capex, no_revenue
- HTO: no_capex, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31
- JOE: capex_below_segment_2024-12-31, capex_below_segment_2023-12-31, capex_below_segment_2025-12-31, current_ltd_untagged_0.1B, debt_one_side_only
- IPGP: no_debt_tagged
- NMRK: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, debt_one_side_only
- RUN: stale_capex, debt_one_side_only
- IDYA: no_debt_tagged
- NTCT: no_debt_tagged
- CIFR: current_ltd_untagged_0.2B
- EROK: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- FBNC: debt_one_side_only
- MCY: debt_one_side_only
- WLTH: no_capex, debt_one_side_only
- VISN: no_debt_tagged, quarters_off_year_revenue_2023-12-31, quarter_exceeds_year_revenue_2024-12-31, quarter_exceeds_year_revenue_2025-12-31, quarters_off_year_revenue_2025-12-31
- PRDO: no_debt_tagged
- FRMI: no_revenue
- APGE: no_debt_tagged, no_revenue
- KLIC: no_debt_tagged
- WOR: debt_one_side_only
- PRVA: stale_capex, no_debt_tagged
- HUT: no_capex, no_debt_tagged
- CARG: no_debt_tagged, debt_one_side_only
- GBX: debt_one_side_only
- ARCB: capex_below_segment_2025-12-31
- NVRI: no_operating_cash_flow, no_capex, no_revenue
- CUBI: debt_one_side_only
- NTSK: no_debt_tagged
- NN: debt_one_side_only
- TMC: no_debt_tagged, no_revenue
- CHCO: debt_one_side_only
- ROCK: quarters_off_year_revenue_2024-12-31
- LMAT: no_debt_tagged
- TARS: debt_one_side_only
- BEAM: debt_one_side_only
- VCYT: no_debt_tagged
- CGON: debt_one_side_only
- SUPN: no_debt_tagged
- HMN: no_capex, debt_one_side_only
- SRPT: debt_one_side_only
- AEO: debt_one_side_only
- NWBI: stale_shares_diluted, no_debt_tagged, quarter_exceeds_year_capex_2024-12-31
- MSDL: no_capex, debt_one_side_only, no_revenue
- WERN: current_ltd_untagged_0.8B, debt_one_side_only
- OCUL: debt_one_side_only
- GEF: stale_revenue, stale_net_income, stale_operating_cash_flow, stale_capex, stale_stock_comp, stale_fcf
- LGND: debt_one_side_only
- SAH: quarter_exceeds_year_capex_2023-12-31, quarter_exceeds_year_capex_2024-12-31, quarter_exceeds_year_capex_2025-12-31
- NIC: quarters_off_year_capex_2024-12-31
- DRH: debt_one_side_only
- SHO: debt_one_side_only
- DNOW: debt_one_side_only
- ROOT: current_ltd_untagged_0.0B, debt_one_side_only
- CWT: no_capex, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31
- ATRC: debt_one_side_only
- SLDE: debt_one_side_only
- NGVT: quarters_off_year_revenue_2024-12-31
- LTC: debt_one_side_only
- INOD: no_debt_tagged
- COLM: no_debt_tagged
- SAM: no_debt_tagged
- MLCI: no_capex, current_ltd_untagged_0.0B, debt_one_side_only
- FBK: debt_one_side_only
- WT: no_debt_tagged
- TDOC: no_debt_tagged
- BKE: stale_stock_comp, no_debt_tagged
- LKFN: no_debt_tagged
- GEMI: no_debt_tagged
- AADX: no_operating_cash_flow, no_capex, no_revenue
- DX: no_capex, no_debt_tagged, no_revenue, interest_but_no_debt
- SAIL: no_debt_tagged, debt_one_side_only
- HNGE: no_debt_tagged
- IMCR: debt_one_side_only
- KN: no_operating_cash_flow, quarters_off_year_revenue_2023-12-31, debt_one_side_only
- XMTR: stale_shares_diluted, no_debt_tagged
- IIPR: stale_capex, current_ltd_untagged_0.0B
- ARR: no_capex, no_debt_tagged, no_revenue
- RPD: no_debt_tagged
- PLUG: no_debt_tagged, interest_but_no_debt
- ARLO: no_debt_tagged
- STBA: debt_one_side_only
- GTY: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, debt_one_side_only
- YELP: no_debt_tagged
- NSSC: no_debt_tagged
- NBHC: stale_capex, debt_one_side_only
- GABC: debt_one_side_only
- MFP: no_operating_cash_flow, no_capex, no_revenue
- POWL: no_debt_tagged
- UMH: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31
- TCBK: no_debt_tagged
- ARWR: no_debt_tagged, interest_but_no_debt
- IRON: debt_one_side_only, no_revenue
- SG: no_debt_tagged
- PD: current_ltd_untagged_0.0B, debt_one_side_only
- VITL: debt_one_side_only
- NAVN: debt_one_side_only, debt_too_small_for_interest
- NTST: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, debt_one_side_only
- CERT: quarters_off_year_revenue_2025-12-31
- APC: no_operating_cash_flow, no_capex, no_revenue
- ADPT: no_debt_tagged
- ATEN: no_debt_tagged
- RSI: no_debt_tagged
- HMH: no_operating_cash_flow, no_capex, no_revenue
- ESRT: current_ltd_untagged_0.2B
- PAY: no_debt_tagged
- FLYW: no_debt_tagged
- NAMS: no_debt_tagged
- MLTX: debt_one_side_only, no_revenue
- LZB: no_debt_tagged
- EFC: stale_shares_diluted, no_debt_tagged, quarter_exceeds_year_capex_2023-12-31
- FA: debt_one_side_only
- AIAI: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- HOPE: debt_one_side_only
- TPB: debt_one_side_only
- OUST: no_debt_tagged
- TVTX: stale_capex, no_debt_tagged
- CLDX: no_debt_tagged
- KALU: debt_one_side_only
- OMCL: no_debt_tagged
- CRGY: quarter_exceeds_year_capex_2025-12-31, debt_one_side_only
- ASAN: debt_one_side_only
- ARI: no_debt_tagged, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, interest_but_no_debt
- TNDM: debt_one_side_only
- LZ: no_debt_tagged
- EVH: stale_capex, debt_one_side_only
- TXG: no_debt_tagged
- VERA: debt_one_side_only, no_revenue
- LUNR: debt_one_side_only
- IOSP: no_debt_tagged
- INVA: debt_one_side_only
- CCB: no_debt_tagged
- CRTO: debt_one_side_only
- FETH: no_capex, no_debt_tagged, no_revenue
- IMVT: no_debt_tagged, no_revenue
- HTH: stale_stock_comp, debt_one_side_only
- TFIN: stale_capex, no_debt_tagged
- CTS: stale_stock_comp, no_debt_tagged
- ROG: no_debt_tagged
- GSBD: no_capex, debt_one_side_only, no_revenue
- OCSL: no_capex, debt_one_side_only, no_revenue
- CMPR: current_ltd_untagged_0.0B
- AMPL: no_debt_tagged
- KLRA: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- CSWC: stale_revenue, debt_one_side_only
- LADR: no_debt_tagged
- HAPN: no_debt_tagged, debt_one_side_only
- VECO: debt_one_side_only
- BELFA: no_debt_tagged, debt_one_side_only
- IMAX: no_debt_tagged, capex_below_segment_2023-12-31
- AIV: quarters_off_year_revenue_2024-12-31, quarters_off_year_revenue_2025-12-31, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, debt_one_side_only, v2 quarterly revenue not used: its quarters did not add up to the year
- CRAI: no_debt_tagged
- EWTX: no_debt_tagged, no_revenue
- COUR: no_debt_tagged
- PEB: current_ltd_untagged_0.0B, debt_one_side_only
- AI: no_debt_tagged
- NEXT: debt_one_side_only
- PWP: no_debt_tagged
- XHR: current_ltd_untagged_0.1B, debt_one_side_only
- SRCE: debt_one_side_only
- WABC: stale_stock_comp, debt_one_side_only
- NVTS: no_debt_tagged
- LIME: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- PBLS: no_operating_cash_flow, no_capex, no_revenue
- RAMP: no_debt_tagged, capex_below_segment_2024-03-31, capex_below_segment_2025-03-31
- FIVN: no_debt_tagged
- SAFT: debt_one_side_only
- VRTS: debt_one_side_only
- BBT: quarters_off_year_revenue_2023-12-31, quarters_off_year_revenue_2024-12-31, debt_one_side_only
- CLOV: no_debt_tagged
- MNKD: debt_one_side_only
- UUUU: debt_one_side_only
- SDGR: no_debt_tagged
- QCRH: debt_one_side_only
- BFC: no_debt_tagged
- CALY: quarter_exceeds_year_capex_2023-12-31, quarter_exceeds_year_capex_2024-12-31, quarter_exceeds_year_capex_2025-12-31, capex_below_segment_2023-12-31, debt_too_small_for_interest
- KNSA: no_debt_tagged
- CIM: no_capex, debt_one_side_only, no_revenue, debt_too_small_for_interest
- TALO: debt_one_side_only
- CNOB: no_debt_tagged
- JANX: no_debt_tagged
- DNLI: no_debt_tagged
- JBGS: no_capex, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31
- TWOD: no_capex, current_ltd_untagged_0.5B, debt_one_side_only, no_revenue
- SPT: debt_one_side_only
- CXM: no_debt_tagged
- HG: no_capex, debt_one_side_only
- SYRE: stale_capex, stale_shares_diluted, no_debt_tagged
- SPHR: stale_capex
- SPRY: quarter_exceeds_year_capex_2023-12-31, debt_one_side_only
- LPG: stale_capex
- WGO: debt_one_side_only
- RLJ: debt_one_side_only
- ATRO: debt_one_side_only
- DCOM: stale_capex, no_debt_tagged
- SABR: quarters_off_year_revenue_2024-12-31, quarters_off_year_operating_cash_flow_2025-12-31
- PFLT: no_capex, no_revenue, debt_too_small_for_interest
- ITG: no_operating_cash_flow, no_capex, no_revenue
- NG: stale_capex, stale_shares_diluted, debt_one_side_only
- USLM: no_debt_tagged, debt_one_side_only
- DBD: debt_one_side_only
- OBK: no_debt_tagged
- LOB: no_debt_tagged
- OMDA: no_debt_tagged, debt_one_side_only
- BHVN: debt_one_side_only, no_revenue
- AAT: revenue_unverified_2025-12-31
- SEDG: no_debt_tagged
- AHCO: quarters_off_year_revenue_2025-12-31, v2 quarterly revenue not used: its quarters did not add up to the year
- CWH: stale_capex, stale_shares_diluted
- BBSI: no_debt_tagged
- VICR: no_debt_tagged
- SFIX: no_debt_tagged
- NVAX: debt_one_side_only
- DGII: debt_one_side_only
- REF: no_operating_cash_flow, no_capex, no_revenue
- CSR: quarters_off_year_capex_2023-12-31, current_ltd_untagged_0.0B, debt_one_side_only
- HROW: debt_one_side_only
- BJRI: debt_one_side_only
- NXTT: stale_capex, quarters_off_year_revenue_2023-12-31, debt_one_side_only
- AZTA: no_debt_tagged
- TRS: quarters_off_year_revenue_2025-12-31, quarters_off_year_capex_2025-12-31, debt_one_side_only, v2 quarterly revenue not used: its quarters did not add up to the year
- IE: no_debt_tagged, quarter_exceeds_year_capex_2025-12-31
- HPP: no_debt_tagged, interest_but_no_debt
- CDNA: no_debt_tagged
- NAVI: no_capex
- AUPH: no_capex, no_debt_tagged
- ACT: no_capex, debt_one_side_only
- SYM: no_debt_tagged
- CNA: debt_one_side_only
- LCLN: no_operating_cash_flow, no_capex, current_ltd_untagged_0.0B, debt_one_side_only, no_revenue
- NVCR: debt_one_side_only
- NMFC: no_capex, debt_one_side_only, no_revenue
- MBIN: no_debt_tagged
- EROC: no_operating_cash_flow, no_capex, no_debt_tagged, debt_one_side_only, no_revenue
- OCFC: debt_one_side_only
- ESTA: debt_one_side_only
- MFA: stale_revenue, stale_capex, no_debt_tagged
- SEI: stale_shares_diluted
- LASR: no_debt_tagged
- AVEX: no_operating_cash_flow, no_capex, no_revenue
- DYN: stale_shares_diluted, debt_one_side_only, no_revenue
- CGBD: no_capex, debt_one_side_only, no_revenue
- DEA: no_capex, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, debt_one_side_only
- VRDN: stale_shares_diluted, debt_one_side_only
- AAMI: no_capex, debt_one_side_only
- ECVT: debt_one_side_only
- COLL: debt_one_side_only, debt_too_small_for_interest
- IART: current_ltd_untagged_0.1B, debt_one_side_only
- IOND: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- TRIN: no_capex, debt_one_side_only, no_revenue
- AMRC: stale_revenue, stale_net_income, stale_operating_cash_flow, stale_capex, stale_stock_comp, stale_fcf
- APOG: debt_one_side_only
- CRMD: debt_one_side_only
- HAWK: no_operating_cash_flow, no_capex, no_debt_tagged, debt_one_side_only, no_revenue
- NHC: no_debt_tagged
- TLRY: stale_capex, debt_one_side_only
- PRLB: no_debt_tagged
- PDM: stale_capex, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, debt_one_side_only
- FMBH: current_ltd_untagged_0.0B, debt_one_side_only
- HCSG: no_debt_tagged
- RDW: capex_below_segment_2024-12-31, capex_below_segment_2025-12-31
- PSEC: no_capex, current_ltd_untagged_0.4B, debt_one_side_only, no_revenue
- WINA: revenue_unverified_2024-12-28, revenue_unverified_2023-12-30, revenue_unverified_2025-12-27, debt_one_side_only
- IDT: no_debt_tagged
- STAA: no_debt_tagged
- ZD: quarters_off_year_revenue_2025-12-31, v2 quarterly revenue not used: its quarters did not add up to the year
- PRAX: no_debt_tagged
- ORC: no_capex, stale_shares_diluted, no_debt_tagged, no_revenue
- TMP: no_debt_tagged, debt_one_side_only
- BY: no_debt_tagged, debt_one_side_only
- NTLA: no_debt_tagged
- PPTA: no_debt_tagged, no_revenue
- ORIC: no_debt_tagged, no_revenue
- GERN: stale_revenue, stale_capex, current_ltd_untagged_0.0B, debt_one_side_only
- FBRT: no_capex, quarters_off_year_revenue_2024-12-31, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31
- HOS: quarters_off_year_revenue_2025-12-31, v2 quarterly revenue not used: its quarters did not add up to the year
- UVSP: debt_one_side_only
- WVE: no_debt_tagged
- SDRL: no_capex, revenue_unverified_2025-12-31, revenue_unverified_2023-12-31, revenue_unverified_2024-12-31, debt_one_side_only
- LQDA: no_debt_tagged
- BLFS: no_debt_tagged, quarters_off_year_revenue_2023-12-31, quarters_off_year_revenue_2025-12-31
- SBSI: debt_one_side_only
- ELVN: no_debt_tagged, no_revenue
- GPCR: no_debt_tagged, no_revenue
- BBDC: no_capex, no_revenue
- MANE: no_debt_tagged, no_revenue
- AMSF: no_debt_tagged
- SONO: stale_capex, no_debt_tagged
- MRTN: no_capex, no_debt_tagged
- PRG: debt_one_side_only
- EIG: quarters_off_year_capex_2023-12-31, quarter_exceeds_year_capex_2024-12-31, quarters_off_year_capex_2024-12-31, quarter_exceeds_year_capex_2025-12-31, quarters_off_year_capex_2025-12-31
- NAGE: stale_capex, no_debt_tagged
- NTGR: no_debt_tagged
- NRIX: no_debt_tagged
- RVLV: no_debt_tagged
- SLRC: no_capex, debt_one_side_only, no_revenue
- FIZZ: no_debt_tagged
- SAFE: stale_capex, revenue_unverified_2023-12-31, current_ltd_untagged_0.0B, debt_one_side_only
- SIBN: debt_one_side_only
- SNDX: debt_one_side_only
- HTZ: current_ltd_untagged_2.3B, debt_one_side_only
- HFWA: stale_stock_comp, debt_one_side_only
- PMT: no_capex, debt_too_small_for_interest
- AGNT: stale_stock_comp, no_debt_tagged
- KOS: capex_below_segment_2024-12-31, capex_below_segment_2023-12-31, capex_below_segment_2025-12-31
- ABCL: no_debt_tagged
- AMN: debt_one_side_only
- EIKN: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- IBTA: no_debt_tagged, debt_one_side_only
- QNST: debt_one_side_only
- BHRB: debt_one_side_only
- DHC: current_ltd_untagged_0.0B, debt_one_side_only
- COGT: stale_revenue, debt_one_side_only
- KW: no_debt_tagged, capex_below_segment_2025-12-31, interest_but_no_debt
- RWT: no_capex, stale_revenue, no_debt_tagged
- QURE: debt_one_side_only, debt_too_small_for_interest
- PAHC: debt_one_side_only
- AVBP: no_capex, no_debt_tagged, no_revenue
- OSBC: debt_one_side_only
- PCRX: debt_one_side_only
- NX: stale_revenue
- BRUN: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- CPF: debt_one_side_only
- CNXN: no_debt_tagged
- BLMN: debt_one_side_only
- MBWM: no_capex, no_debt_tagged
- BLLN: debt_one_side_only
- KARD: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- SXC: debt_one_side_only
- CFFN: no_debt_tagged, quarter_exceeds_year_revenue_2023-09-30
- VIA: no_debt_tagged
- AMTB: no_debt_tagged
- UVE: debt_one_side_only
- SCHL: current_ltd_untagged_0.0B
- ADTN: no_debt_tagged
- SEB: debt_one_side_only
- AD: quarter_exceeds_year_revenue_2023-12-31, quarter_exceeds_year_revenue_2024-12-31, quarters_off_year_revenue_2024-12-31, quarter_exceeds_year_capex_2023-12-31, quarter_exceeds_year_capex_2024-12-31, capex_below_segment_2024-12-31, capex_below_segment_2023-12-31
- RMIX: no_operating_cash_flow, no_capex, no_revenue
- BFST: no_debt_tagged, quarter_exceeds_year_capex_2025-12-31
- MCB: stale_capex, no_debt_tagged
- RC: no_capex, quarter_exceeds_year_revenue_2024-12-31, current_ltd_untagged_0.1B, debt_one_side_only
- UFCS: no_capex, debt_one_side_only
- EQBK: current_ltd_untagged_0.4B, debt_one_side_only
- OPY: no_debt_tagged, interest_but_no_debt
- WMK: no_debt_tagged
- EZPW: debt_one_side_only
- ACH: quarter_exceeds_year_revenue_2023-12-31, quarters_off_year_revenue_2024-12-31
- CAC: debt_one_side_only
- ANGI: quarters_off_year_operating_cash_flow_2023-12-31, debt_one_side_only
- FG: debt_one_side_only
- KE: debt_one_side_only
- CRI: debt_one_side_only
- HBNC: quarter_exceeds_year_revenue_2025-12-31, current_ltd_untagged_0.1B, debt_one_side_only
- IBCP: no_debt_tagged
- MAGN: debt_one_side_only
- TFSL: no_debt_tagged
- GOLD: capex_below_segment_2024-06-30, debt_too_small_for_interest
- KFRC: no_debt_tagged
- ASIX: no_debt_tagged
- RBCAA: no_debt_tagged
- MTUS: no_debt_tagged
- BXC: debt_one_side_only
- XRX: stale_shares_diluted, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31
- TRST: debt_one_side_only
- PXED: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- TBLA: debt_one_side_only
- MPB: debt_one_side_only
- NBBK: no_debt_tagged
- TRLV: debt_too_small_for_interest
- FWRD: quarters_off_year_operating_cash_flow_2023-12-31, quarters_off_year_capex_2023-12-31, debt_one_side_only
- ORRF: no_debt_tagged
- ADAM: debt_one_side_only, no_revenue
- GDOT: debt_one_side_only
- THFF: current_ltd_untagged_0.3B, debt_one_side_only
- TIPT: no_debt_tagged, quarter_exceeds_year_revenue_2023-12-31, quarter_exceeds_year_revenue_2024-12-31, quarter_exceeds_year_revenue_2025-12-31, quarters_off_year_revenue_2025-12-31, quarter_exceeds_year_capex_2023-12-31, quarter_exceeds_year_capex_2024-12-31, v2 quarterly revenue not used: its quarters did not add up to the year
- SMBC: no_debt_tagged
- GENB: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- AKTS: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- PTRN: no_debt_tagged
- AMAL: no_debt_tagged, quarter_exceeds_year_capex_2025-12-31
- WASH: no_debt_tagged
- SMBK: debt_one_side_only
- WHK: no_operating_cash_flow, no_capex, no_revenue
- IVR: no_capex, stale_revenue, stale_stock_comp, no_debt_tagged
- DMII: no_capex, debt_one_side_only, no_revenue
- GCT: no_debt_tagged
- GSBC: debt_one_side_only
- ODTX: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- SHBI: debt_one_side_only
- HYNE: no_debt_tagged
- HAFC: no_debt_tagged
- KREF: no_debt_tagged, interest_but_no_debt
- DFH: debt_one_side_only
- FSBC: no_debt_tagged
- BCSS: no_capex, no_debt_tagged, no_revenue
- COAG: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- MSBI: debt_one_side_only
- PGC: stale_stock_comp, debt_one_side_only
- JACK: stale_operating_cash_flow
- ARHS: no_debt_tagged
- PFIS: quarter_exceeds_year_capex_2024-12-31, debt_one_side_only
- HOV: debt_one_side_only
- KRNY: no_debt_tagged
- SPFI: no_debt_tagged
- SPTX: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- NFBK: no_debt_tagged
- AMBQ: no_capex, no_debt_tagged
- AVLN: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- BKV: quarters_off_year_revenue_2024-12-31, quarters_off_year_revenue_2025-12-31, v2 quarterly revenue not used: its quarters did not add up to the year
- CAL: no_debt_tagged
- SUJA: no_operating_cash_flow, no_capex, no_revenue
- CXII: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- CCO: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31
- TCBX: stale_capex, no_debt_tagged
- GRDN: no_debt_tagged, debt_one_side_only
- CNDT: quarters_off_year_revenue_2025-12-31, v2 quarterly revenue not used: its quarters did not add up to the year
- GCGR: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- FOR: revenue_unverified_2025-09-30, revenue_unverified_2023-09-30, revenue_unverified_2024-09-30, debt_one_side_only
- FSUN: no_debt_tagged
- CCRN: no_debt_tagged
- SVC: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31
- ALMR: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- NBR: debt_one_side_only
- STGW: debt_one_side_only
- TITN: stale_capex
- XZO: no_debt_tagged
- ARKO: quarter_exceeds_year_revenue_2023-12-31, quarters_off_year_revenue_2023-12-31, revenue_unverified_2023-12-31
- NPB: no_debt_tagged
- OXM: debt_one_side_only
- MPLT: no_debt_tagged, no_revenue
- GIC: no_debt_tagged
- MLAA: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- KODK: debt_too_small_for_interest
- KELYA: debt_one_side_only
- LBRX: no_debt_tagged, no_revenue
- GHXIU: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- BRR: no_operating_cash_flow, no_capex, no_revenue
- KRSP: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- SHOE: no_debt_tagged
- IACO: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- AEXA: no_capex, no_debt_tagged, no_revenue
- CLBK: debt_one_side_only
- APXT: no_capex, stale_shares_diluted, no_debt_tagged, no_revenue
- CRAN: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- NWAX: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- MESH: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- KBON: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- KRAQ: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- IEAG: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- BWB: no_debt_tagged
- HTFL: no_debt_tagged
- OPEN: no_debt_tagged, interest_but_no_debt
- CWBC: debt_one_side_only
- SSMR: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- GBFH: no_debt_tagged, debt_one_side_only
- ARES: stale_capex, no_debt_tagged, revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31, interest_but_no_debt
- ARDT: no_capex
- CMP: debt_one_side_only
- GUAC: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- HBT: stale_capex, no_debt_tagged
- ACCO: stale_capex
- HGTY: stale_shares_diluted, debt_one_side_only
- FLNC: no_debt_tagged
- MEVO: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- MZYX: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- ALOV: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- CLBR: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- EVMN: no_debt_tagged
- ILPT: debt_one_side_only
- BBCQ: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- ZKP: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- OIM: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- FVAV: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- DBCA: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- HACQ: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- ATLCP: stale_capex, no_debt_tagged
- KEYY: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- BCARU: no_operating_cash_flow, no_capex, stale_shares_diluted, no_debt_tagged, no_revenue
- ACAA: no_operating_cash_flow, no_capex, no_revenue
- ELMT: no_operating_cash_flow, no_capex, current_ltd_untagged_0.0B, debt_one_side_only, no_revenue
- ARCI: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- RNA: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- ONIT: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31
- CGCFU: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- CCII: no_capex, stale_shares_diluted, no_debt_tagged, no_revenue
- HCMA: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- BDCI: no_capex, stale_shares_diluted, no_debt_tagged, no_revenue
- GIW: no_capex, no_debt_tagged
- ARTC: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- SORN: no_operating_cash_flow, no_capex, no_revenue
- TLNC: no_operating_cash_flow, no_capex, no_revenue
- GIX: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- DSGR: quarters_off_year_capex_2024-12-31, quarters_off_year_capex_2025-12-31, v2 quarterly capex not used: its quarters did not add up to the year
- IPFX: no_operating_cash_flow, no_capex, no_debt_tagged, debt_one_side_only, no_revenue
- CAII: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- DSAC: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- IACQ: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- AACI: no_operating_cash_flow, no_capex, no_debt_tagged, debt_one_side_only, no_revenue
- RREV: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- CAES: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- EVOX: no_operating_cash_flow, no_capex, stale_shares_diluted, no_debt_tagged, no_revenue
- RYAM: stale_capex
- SGP: no_debt_tagged, no_revenue
- XRPN: no_capex, no_debt_tagged, no_revenue
- KOYN: no_capex, no_debt_tagged, no_revenue
- RNGT: no_capex, no_debt_tagged, no_revenue
- VHCP: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- VACI: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- SAC: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- GPAC: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- ADAC: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- ITHA: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- QLEP: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- LEGO: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- SAAQ: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- KCAC-UN: no_operating_cash_flow, no_capex, no_debt_tagged, debt_one_side_only, no_revenue
- MTAL: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- IPXG: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- CAQ: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- AACO: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- SVIV: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- TMTS: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- IRHO: no_capex, no_debt_tagged, no_revenue
- KPET: no_operating_cash_flow, no_capex, no_revenue
- ILLU: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- GSRV: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- USDE: no_operating_cash_flow, no_capex, no_revenue
- FGII: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- FTRA: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- YICC: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- WLCOU: no_operating_cash_flow, no_capex, no_revenue
- XCBE: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- ISNR: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- BIXI: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- MTNE: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- SIND: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- SVAQ: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- ACGC: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- SHOT: no_operating_cash_flow, no_capex, no_revenue
- QMLS: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- INBK: debt_one_side_only
- MITT: no_capex, stale_revenue, no_debt_tagged
- HCAC: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- TRGS: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- XSLL: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- PAII: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- DNMX: no_operating_cash_flow, no_capex, stale_shares_diluted, no_debt_tagged, no_revenue
- BNED: debt_one_side_only
- MUZE: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- VEL: no_debt_tagged, no_revenue
- NHIV: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- IPVV: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- OFRM: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- QADR: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- TBI: debt_one_side_only
- KSS: debt_one_side_only
- APMD: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- MOBI: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- DOUG: no_debt_tagged, debt_one_side_only
- STRZ: quarter_exceeds_year_revenue_2024-03-31, quarters_off_year_revenue_2025-03-31, quarters_off_year_operating_cash_flow_2025-03-31, quarters_off_year_capex_2025-03-31
- PARK: no_operating_cash_flow, no_capex, no_revenue
- OHAC: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- ONEW: stale_shares_diluted
- TRAX: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- SSP: stale_stock_comp
- GTERA: no_capex, stale_shares_diluted, no_debt_tagged, no_revenue
- MKLY: no_capex, stale_shares_diluted, no_debt_tagged, no_revenue
- PTAC: no_operating_cash_flow, no_capex, no_revenue
- DYOR: no_capex, no_debt_tagged, no_revenue
- TDWD: no_operating_cash_flow, no_capex, no_revenue
- IGAC: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- BLRK: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- BIII: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- LTGR: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- SUMA: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- SSAC: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- AACP: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- TVIV: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- SWRD: no_operating_cash_flow, no_capex, no_revenue
- ATLQ: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- IRAB: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- PALO: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- DGAC: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- IDAC: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- WBTN: no_debt_tagged
- LESL: debt_one_side_only
- BEBE: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- ETSS: no_operating_cash_flow, no_capex, no_revenue
- SI: debt_one_side_only
- LE: no_debt_tagged
- HAVA: no_capex, stale_shares_diluted, debt_one_side_only, no_revenue
- LFAC: no_operating_cash_flow, no_capex, stale_shares_diluted, no_debt_tagged, debt_one_side_only, no_revenue
- WLII: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- STDN: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- APMC: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- IHRT: revenue_unverified_2024-12-31, revenue_unverified_2023-12-31, revenue_unverified_2025-12-31
- AESP: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- FOA: stale_capex, stale_stock_comp, quarter_exceeds_year_revenue_2023-12-31
- AIIA: no_capex, no_debt_tagged, no_revenue
- BID: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- KTWO: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- KRO: debt_one_side_only
- RHLD: quarters_off_year_operating_cash_flow_2024-12-31
- PAAC: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- BWIV: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- CHEC: no_capex, no_debt_tagged, no_revenue
- ADV: quarter_exceeds_year_capex_2024-12-31, quarter_exceeds_year_capex_2025-12-31
- ATTO: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- CTAA: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- BRVE: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- BLSM: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- ARCL: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- PONO: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- INAC: no_capex, stale_shares_diluted, no_debt_tagged, no_revenue
- NMP: no_capex, stale_shares_diluted, no_debt_tagged, no_revenue
- SPEG: no_capex, stale_shares_diluted, no_debt_tagged, no_revenue
- EMIS: no_operating_cash_flow, no_capex, stale_shares_diluted, no_debt_tagged, no_revenue
- WPAC: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- LAFA: no_capex, stale_shares_diluted, no_debt_tagged, no_revenue
- LKSP: no_capex, no_debt_tagged, no_revenue
- CARL: debt_one_side_only
- WENC: no_operating_cash_flow, no_capex, no_debt_tagged, debt_one_side_only, no_revenue
- QRED: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- GLED: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- CEPS: no_capex, no_debt_tagged, no_revenue
- ALPX: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- NREF: no_capex, no_revenue
- TRAD: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- FMAC: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- AVAT: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- PLUN: no_operating_cash_flow, no_capex, no_debt_tagged, debt_one_side_only, no_revenue
- OTAI: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- LDI: debt_one_side_only
- UAC: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- APUR: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- SBMT: no_operating_cash_flow, no_capex, no_revenue
- SCPQ: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- REA: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- RFAM: no_operating_cash_flow, no_capex, no_revenue
- NP: no_capex, no_debt_tagged
- FTHA: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- VECA: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- BHAV: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- XFLH: no_operating_cash_flow, no_capex, no_debt_tagged, debt_one_side_only, no_revenue
- MYX: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- NKLR: no_capex, no_debt_tagged, no_revenue
- TTEC: no_debt_tagged, interest_but_no_debt
- BKKT: stale_capex, no_debt_tagged
- FXAC: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- FWAC: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- RRGB: debt_one_side_only
- BRKH: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- CHPG: no_capex, stale_shares_diluted, no_debt_tagged, no_revenue
- AMAN: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- RACC: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- ORIQ: no_capex, stale_shares_diluted, no_debt_tagged, no_revenue
- MMTX: no_operating_cash_flow, no_capex, stale_shares_diluted, no_debt_tagged, no_revenue
- GFUZ: no_operating_cash_flow, no_capex, stale_shares_diluted, no_debt_tagged, no_revenue
- GLND: no_operating_cash_flow, no_capex, no_revenue
- LTGO: no_operating_cash_flow, no_capex, no_revenue
- JATT: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- ALIS: no_capex, stale_shares_diluted, no_debt_tagged, no_revenue
- PECE: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- MCAH: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- NBRG: no_capex, no_debt_tagged, no_revenue
- APAC: no_capex, debt_one_side_only, no_revenue
- BPAC: no_capex, stale_shares_diluted, debt_one_side_only, no_revenue
- WSTN: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- SCTX: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- OBX: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- BSEM: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- DMRC: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- ENHA: no_capex, no_debt_tagged, no_revenue
- NUCL: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- RDNW: debt_too_small_for_interest
- PLCE: debt_one_side_only
- AHT: debt_one_side_only
- SWMR: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- TYGO: debt_one_side_only
- RJET: quarters_off_year_revenue_2024-12-31, quarters_off_year_revenue_2025-12-31, quarters_off_year_operating_cash_flow_2024-12-31, quarters_off_year_operating_cash_flow_2025-12-31, quarters_off_year_capex_2024-12-31, v2 quarterly revenue not used: its quarters did not add up to the year
- SEV: no_debt_tagged, no_revenue
- AMSS: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- VATE: quarters_off_year_capex_2025-12-31, v2 quarterly capex not used: its quarters did not add up to the year
- AENT: no_debt_tagged, revenue_unverified_2026-06-30, revenue_unverified_2025-06-30, revenue_unverified_2024-06-30
- NUTR: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- ADBT: no_operating_cash_flow, no_capex, no_revenue
- BUDA: debt_one_side_only
- ROC: no_capex, no_debt_tagged
- NOMA: no_capex, no_debt_tagged
- CV: no_debt_tagged
- VIDA: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- DIT: debt_one_side_only
- FBDT: no_operating_cash_flow, no_capex, no_revenue
- TTRX: no_capex, current_ltd_untagged_0.0B, debt_one_side_only, no_revenue
- VTIX: no_capex
- PLYX: no_capex, no_debt_tagged, no_revenue
- EXYN: no_operating_cash_flow, no_capex, no_revenue
- AAC-UN: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- ELWT: no_capex
- VHUB: debt_one_side_only
- CNXU: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- AIDX: no_capex, no_debt_tagged
- CURX: no_capex, no_debt_tagged, no_revenue
- LABT: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- ATHR: quarters_off_year_operating_cash_flow_2025-09-30, debt_one_side_only
- BMNR: no_debt_tagged, quarter_exceeds_year_capex_2024-08-31
- PTCT: quarter_exceeds_year_capex_2024-12-31
- CYAB: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- VOGX: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- GYGY: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- THEO: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- EWAV: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- CAST: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- SAMO-UN: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- JONEU: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- MRCO: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- RACD: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- BCCQ: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- BREZ: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- OSPRU: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- NCO: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- MIACU: no_operating_cash_flow, no_capex, no_revenue
- AMACU: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- VII: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- BRTMU: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- FJDIU: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- FDMM: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- TCGX: no_operating_cash_flow, no_capex, no_revenue
- MTAKU: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- CATLU: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- CCCT: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- TBCVU: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- SAGU: no_operating_cash_flow, no_capex, no_debt_tagged, no_revenue
- PNAQ-UN: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue
- SECZ: no_operating_cash_flow, no_capex, no_revenue
- JMKE: no_operating_cash_flow, no_capex, no_revenue
- FTW: no_operating_cash_flow, no_capex, no_revenue
- JBS: no_operating_cash_flow, no_capex, no_revenue
- XPRO: no_operating_cash_flow, no_capex, debt_one_side_only, no_revenue

## Largest 25 by public float

| ticker | public float | revenue TTM | capex TTM | total debt | shares |
|---|---|---|---|---|---|
| CBT | 4,429,047.30B | 3.63B | 0.22B | 1.27B | 51.6M |
| OLED | 6,792.43B | 0.61B | 42.2M | 1.1M | 46.0M |
| ONTO | 4,817.28B | 1.12B | 13.8M | - | 49.1M |
| TTMI | 4,165.94B | 3.38B | 0.34B | 0.97B | 0.11B |
| SKY | 4,135.96B | 2.67B | 35.1M | 23.8M | 54.3M |
| NVDA | 4,000.00B | 302.97B | 7.35B | 33.37B | 24.10B |
| MSFT | 3,600.00B | 331.84B | 115.95B | 40.29B | 7.43B |
| NOVT | 3,496.56B | 1.03B | 19.6M | 0.23B | 37.8M |
| AAPL | 3,253.43B | 466.82B | 10.04B | 84.34B | 14.59B |
| MGRC | 2,853.95B | 0.93B | 42.2M | 0.59B | 24.4M |
| ENVA | 2,669.87B | 3.45B | 46.4M | 5.01B | 24.9M |
| RENX | 2,290.41B | 15.0M | 3.6M | 39.2M | 2.6M |
| AMZN | 2,118.06B | 775.68B | 173.03B | 132.55B | 10.79B |
| CLSK | 1,967.00B | 0.77B | 91.3M | 1.78B | 0.26B |
| GOOGL | 1,900.00B | 445.87B | 132.40B | 100.16B | 12.23B |
| META | 1,600.00B | 228.25B | 89.33B | 83.66B | 2.55B |
| TRMK | 961.60B | 0.82B | 20.8M | - | 58.1M |
| HIVE | 950.74B | 0.30B | 21.6M | 1.6M | 0.27B |
| AVGO | 939.20B | 89.10B | 1.25B | 61.08B | 4.77B |
| BRK-B | 902.70B | 384.69B | 22.42B | - | 2.14B |
| TSLA | 892.93B | 103.62B | 12.92B | 9.06B | 3.95B |
| THRM | 853.97B | 1.58B | 46.1M | 0.27B | 30.7M |
| WTTR | 837.40B | 1.43B | 0.32B | 0.26B | 0.14B |
| LLY | 807.89B | 79.67B | 9.89B | 54.91B | 0.94B |
| JPM | 794.43B | 199.41B | - | 72.43B | 2.66B |
