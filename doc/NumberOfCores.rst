===========================================
How to choose the right number of CPU cores
===========================================

The amount of cores you can ask for ``abx-distance`` is only limited by the
number of cores available on the machine you're using (unless you have very big
"BY" blocks in your features file, in which case you need to make sure
Size-of-the-biggest-BY-block*number-of-cores does not exceed the available
memory).

The running time is going to be essentially
number-of-distances-to-be-computed*time-required-to-compute-a-distance. You can
get an estimate of that easily by taking a smaller item file, obtaining the
number of distances to be computed with the original item file n and with the
smaller file **n_small**. You then run the ABX evaluation for the smaller file
and look at the time **t_small** it takes using only 1 core. Then you can
estimate the time it will take for the bigger file using **n_cores** cores: **t
= t_small*n/(n_small*n_cores)**.

If the estimated time is too long given your deadlines, you can reduce the
number of pairs to be computed without compromising your results by sampling the
item file. You have to do it in a way that make sense given the ABX task you are
using and the analyses you want to do. For example for a task "ON phoneme BY
speaker, context":

* For any (phoneme, speaker, context) triple that appears on more than **k**
  lines in the item file, you can keep **k** lines only (randomly sampled).
  **k=10** or even **k=5** should be largely sufficient, unless you are not
  averaging over speakers and contexts in your analyses.
* You can also remove any line with a (phoneme, speaker, context) triple that
  appears only once in the item file, as those cannot be used to estimate
  symetrised scores (unless you are interested in the asymetries).
