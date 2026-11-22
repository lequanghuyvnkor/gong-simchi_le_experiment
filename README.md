# Gong & Simchi-Levi — Inventory Learning Experiments

A small, reproducible research workspace for learning and studying cyclic-demand inventory algorithms. It contains a Vietnamese interactive simulator, a five-experiment teaching notebook, and a focused ablation of HQL learning-rate schedules.

## Contents

- **`lost_sales_lab/`** — Streamlit simulator for inventory operations and step-by-step HQL, Meta-HQL, and FQL learning. Mimic-QL is not implemented yet. See its [README](lost_sales_lab/README.md) for model assumptions and controls.
- **`notebooks/gong_simchi_5_experiments.ipynb`** — notebook for a 45-minute presentation: cyclic demand, inventory handoffs, volatility, risk-sensitive policies, and capital cost / order-wait decisions.
- **`.work/run_alpha_demo.py`** — script that runs the alpha-schedule experiment. The leading-dot folder keeps the script path consistent with the workspace layout it was developed for.
- **`results/five_experiments/`** — saved configuration, manifest, CSV summaries and plots from the quick notebook run.
- **`results/alpha_sensitivity/`** — saved configuration, report, summary, plots and per-run NPZ traces for the alpha experiment.

## Run the simulator

Python 3.10 or newer is recommended. From the repository root:

```powershell
python -m pip install -r lost_sales_lab/requirements.txt
python -m streamlit run lost_sales_lab/app.py
```

Open <http://127.0.0.1:8501>. To open a particular model in a fresh session, use `?model=hql`, `?model=meta`, or `?model=fql`. The simulator README explains the inventory rules, censored sales feedback, costs, and the limits of each comparison.

## Run the notebook

Install Jupyter and the notebook dependencies if they are not already available:

```powershell
python -m pip install numpy pandas matplotlib scipy ipython ipykernel jupyter
jupyter notebook notebooks/gong_simchi_5_experiments.ipynb
```

Run all cells from top to bottom. The notebook uses synthetic demand and does not download external datasets. Its saved results are in `results/five_experiments/`.

## Run the alpha-schedule experiment

From the repository root:

```powershell
python -m pip install numpy pandas matplotlib
python .work/run_alpha_demo.py
```

The script writes refreshed outputs to `results/alpha_sensitivity/`. It compares five learning-rate schedules over five demand scenarios and paired seeds. The result is a teaching and sensitivity experiment on the app's discrete HQL implementation, not a general ranking of learning-rate formulas.

## Reading the results

The five-experiment notebook is configured in **quick** mode. TN1–TN3 use a practical finite-grid Meta-HQL variant. TN4–TN5 use known-distribution dynamic programming extensions. They are distinct experiments and should not be described as a single theoretical replication of the paper.

The alpha experiment uses a discrete inventory grid from the simulator, lost sales, and episodic episodes. The original confidence threshold is so conservative that the candidate set may not shrink over the simulated horizon. Runs with a smaller illustrative threshold are labeled as an illustration and do not inherit the paper's theoretical guarantee. The level-shift demand scenario is a stress test outside the repeated-distribution assumption.

The simulator is an educational implementation. Its manual-vs-learner comparison uses a shared demand path and is descriptive; it is not, by itself, an estimate of expected regret or a proof of optimality.

## Scope and attribution

This repository contains independent educational and experimental implementations inspired by Gong and Simchi-Levi's *Bandits atop Reinforcement Learning: Tackling Online Inventory Models with Cyclic Demands* (Manufacturing & Service Operations Management, 2024). It does not include the authors' replication package or claim to reproduce all published results. See the original article and supplementary materials before interpreting algorithm details or theoretical claims.

The saved alpha results and notebook outputs are provided for transparency. Re-running scripts can produce small numeric differences across Python and library versions. The package records configurations and software versions where available.

## License

No license has been selected for this repository yet. Until a license is added, assume that reuse, redistribution, and derivative works require the copyright holder's permission. The research paper and any third-party data or materials remain subject to their own terms.
