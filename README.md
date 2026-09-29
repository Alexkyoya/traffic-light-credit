🚦 Traffic Light Credit Decisions

Can a bank decide more personal loan applications automatically, without taking on more risk?

This project builds a probability of default (PD) model on public personal loan data, then turns it into a simple decision rule:

🟢 Green: low risk, approved instantly
🟡 Yellow: uncertain, reviewed by an analyst
🔴 Red: high risk, declined instantly

Every automated decision comes with its main reasons, so it can be explained to a client, an analyst or a validator.

👉 Try the interactive simulator (in French): move the thresholds and see the automation rate, the risk in the green zone and the estimated losses change in real time.

Headline result

To be completed from step 23 of the notebook:

With the green zone covering the 40% least risky applicants and the red zone the 10% most risky, X% of applications are decided automatically. The default rate in the green zone is Y%, versus 12.2% on average, and the red zone stops Z% of all defaults.

Data

Lending Club personal loans (U.S.), teaching version available on Kaggle (lending_club_loan_two.csv). Each loan has the information known at application (income, debt-to-income ratio, credit history, purpose, etc.) and its final outcome: fully paid or charged off.

Scope: 36-month loans issued from 2010 to 2013, 133,503 loans in total.

Set	Years	Loans	Default rate
Training	2010–2012	53,137	12.4%
Test (out-of-time)	2013	80,366	12.2%
Key decisions
1. Detecting selection bias

The dataset only keeps loans with a final outcome. For recent years, many loans had not matured yet, and those that ended early were more often defaults. The default rate by year makes this visible:

Year	2010	2011	2012	2013	2014
Default rate (36-month loans)	10.4%	10.6%	13.4%	12.2%	18.9%

The jump in 2014 is not real risk: it is incomplete data. 2014 and later loans were excluded, and 60-month loans too, since they take longer to mature.

2. Out-of-time validation

The model is trained on 2010–2012 and tested on 2013, like a bank that builds a model on past data and uses it on new clients. A random split would mix periods and look better than reality.

3. Not copying Lending Club's own model

Lending Club's grade, sub-grade, interest rate and instalment were excluded. They are outputs of the platform's own risk model: using them would mean copying its answer instead of building a model from application data.

4. No class rebalancing

Only 12% of loans default, but the classes were not rebalanced. In credit risk, the predicted probability must stay realistic, because it feeds expected loss, pricing and capital.

5. Champion vs. challenger

A transparent logistic regression (the basis of bank scorecards) was compared with LightGBM. The challenger only replaces the champion if the gain is clear (AUC +0.01 or more).

Results
Model	Test AUC	Test Gini
Logistic regression	0.620	0.240
Logistic regression without loan_amnt (retained)	0.618	0.237
LightGBM	0.627	0.254
Retained model: logistic regression without loan_amnt. Removing it cost almost nothing and fixed a counterintuitive sign (the loan amount overlaps with income and loan-to-income ratio).
LightGBM gained only +0.007 AUC, below the threshold: not worth the loss of transparency.
No overfitting: train and test performance are close (AUC 0.635 vs. 0.620 for the logistic regression).
Calibration: mean predicted PD of 12.8% vs. 12.2% observed, with close values in every risk decile. The model slightly overestimates risk, which is the safer direction.
Modest discrimination is expected: this dataset has no credit bureau score (such as FICO), usually the strongest predictor in retail credit.
Reason codes

For a logistic regression, each variable's contribution to a client's risk is simply its coefficient times the client's standardized value. The top three positive contributions become the reasons for a yellow or red decision (for example: high debt-to-income ratio, public record, small business loan).

Limitations
Approved loans only: we do not know what would have happened to declined applicants (reject inference is not addressed).
Yellow zone: we assume analysts review these files as they do today.
Proxy data: U.S. data, used as an example; not representative of the Canadian market.
Losses: the simulator applies an assumed loss given default (LGD) to the initial loan amount, a simplification.
Prototype: built for learning, not a production system.
Project structure
traffic-light-credit/
├── data/                  ← raw data (not tracked)
├── notebook/
│   └── 01_data.ipynb      ← full analysis, with notes in French
├── app/
│   └── simulateur.csv     ← 100 aggregated risk groups for the simulator
└── README.md
How to run
Download lending_club_loan_two.csv and lending_club_info.csv from Kaggle into data/.
Create an environment and install the packages:
bash
   python -m venv .venv
   pip install pandas numpy scikit-learn lightgbm matplotlib pyarrow jupyter
Open notebook/01_data.ipynb and run all cells.
Author

Alex (Qichao) Zhao, MMA candidate, McGill University