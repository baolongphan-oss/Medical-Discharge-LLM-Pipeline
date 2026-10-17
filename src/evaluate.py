# Stage 3: Evaluation (Oct 14–15)
# Hand-label medications and doses for 30 to 50 test notes in a JSON file. This is tedious, but it's your ground truth.
# In src/evaluate.py, compute validation pass rate, medication recall and precision, hallucinated-dose rate, and average reading grade.
# Write extract_v2.txt (improved using dev notes only) and run both versions on the test set.
# Save results to dated files that include the model name. In notebooks/evaluation.ipynb, build the v1 versus v2 results table.
# Write a first README: problem, approach, results table, limitations, how to run. Push to GitHub.