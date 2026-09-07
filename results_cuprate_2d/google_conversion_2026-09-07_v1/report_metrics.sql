SELECT case_name, method, count(*) AS sites,
 sum(charge) AS N, avg(doublon) AS mean_D,
 sqrt(avg(spin*spin)) AS spin_RMS,
 avg(ref_doublon) AS ref_D, sqrt(avg(ref_spin*ref_spin)) AS ref_spin_RMS,
 sqrt(avg((charge-ref_charge)*(charge-ref_charge))) AS rms_charge,
 sqrt(avg((spin-ref_spin)*(spin-ref_spin))) AS rms_spin,
 sqrt(avg((doublon-ref_doublon)*(doublon-ref_doublon))) AS rms_D
 FROM local_profiles GROUP BY case_name, method ORDER BY case_name, method;
