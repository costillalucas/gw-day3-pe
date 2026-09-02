# Point 2: notebook vs CLI numerical comparison

## mchirp_guess (deterministic: same seed, same zero-crossing fit)

notebook: 21.23844134253563
CLI:      21.23844134253563
abs diff: 0.000e+00  -> MATCH (exact/float-precision)

## par_dic_0 (deterministic reference waveform)

param                   notebook               CLI      abs diff  verdict
d_luminosity             758.252           758.252     0.000e+00  MATCH
dec                    -0.379515         -0.379515     0.000e+00  MATCH
f_ref                        100               100     0.000e+00  MATCH
iota                     2.14159           2.14159     0.000e+00  MATCH
l1                             0                 0     0.000e+00  MATCH
l2                             0                 0     0.000e+00  MATCH
m1                       161.137           161.137     0.000e+00  MATCH
m2                       11.0272           11.0272     0.000e+00  MATCH
phi_ref                 -1.03093          -1.03093     0.000e+00  MATCH
psi                            0                 0     0.000e+00  MATCH
ra                       2.12049           2.12049     0.000e+00  MATCH
s1x_n                          0                 0     0.000e+00  MATCH
s1y_n                          0                 0     0.000e+00  MATCH
s1z                     0.989398          0.989398     0.000e+00  MATCH
s2x_n                          0                 0     0.000e+00  MATCH
s2y_n                          0                 0     0.000e+00  MATCH
s2z                     0.989398          0.989398     0.000e+00  MATCH
t_geocenter              1.54272           1.54272     0.000e+00  MATCH

=> par_dic_0 overall: MATCH

## posterior medians (stochastic: independent Nautilus runs)

param              nb median     nb SE    cli median    cli SE      |diff|       z  verdict
m1                   157.265     0.054       157.357     0.055      0.0925    1.20  MATCH
m2                   10.0116     0.007       10.0115    0.0069    9.17e-05    0.01  MATCH
s1z                 0.988392    0.0001       0.98842    0.0001     2.8e-05    0.20  MATCH
s2z                0.0542902    0.0077     0.0593485    0.0076     0.00506    0.47  MATCH
d_luminosity         1004.03       2.6       1007.04       2.5        3.01    0.84  MATCH
ra                   2.13661   0.00066       2.13559   0.00065     0.00102    1.11  MATCH
dec                -0.396802   0.00087     -0.396246   0.00086    0.000556    0.45  MATCH
phi_ref              3.16547     0.025       3.13608     0.025      0.0294    0.83  MATCH
psi                  1.57199     0.012       1.56564     0.012     0.00635    0.36  MATCH
iota                 2.55982    0.0038       2.56177    0.0038     0.00195    0.36  MATCH
t_geocenter          1.54424   2.6e-05       1.54429   2.6e-05    5.68e-05    1.56  MATCH
lnl                  202.884     0.032       202.923     0.031      0.0387    0.88  MATCH

=> medians within 3.0 sigma: 12/12

## log evidence (stochastic: independent nested-sampling runs)

notebook: lnZ = 156.3139 +/- 0.0110  (n_eff=8271)
CLI:      lnZ = 156.3293 +/- 0.0109  (n_eff=8374)
|diff| = 0.0154, combined SE = 0.0155, z = 1.00  -> MATCH (threshold z <= 3.0)

