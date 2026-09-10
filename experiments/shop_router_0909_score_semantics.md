# Shop Router 0909 score semantics

The selected notebook does not claim a percentage win rate. Its strength signal is a Kaggriculture competition rating, not a local win-rate statistic.

At the scan timestamp, the notebook-level live listing showed **2847.4**. The public v1 page separately exposes submission **56113158**, score **2839.5**, and `sourceScriptVersionId=348430185`. That is the strongest source-to-score relationship that can be verified exactly from the acquired metadata, so v1/run 348430185 is the formal reproduction target.

The 2847.4 live value and 2839.5 stored version-linked value must not be conflated. Kaggle's live game rating can move as evaluation episodes accumulate or the competition population changes. The live kernel value establishes discovery-time competitive strength; it does not prove that current v3 produced that exact value. V2 and v3 are nevertheless behaviorally equivalent to v1 because their decoded `main.py` and `actions.json` are byte-identical.

The local **64/64 broad-league wins** and **16/16 direct CurrentBest wins** are outcomes only for the controlled panels in this repository. They do not estimate the notebook's Kaggle-wide win rate and must not be presented as its leaderboard win rate.

The earlier Public State Router headline “93.8% Win Rate” is not evaluated or repeated here because the recency/score scan selected a different target.
