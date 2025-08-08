import yaml

with open('./questions/questions.yml', 'r') as qf:
    questions = yaml.safe_load(qf)

with open('./solutions/solutions.yml', 'r') as sf:
    solutions = yaml.safe_load(sf)

question_ids = {q['id'] for q in questions}
solution_ids = set(map(int, solutions.keys()))

missing_in_solutions = question_ids - solution_ids
orphans_in_solutions = solution_ids - question_ids

print("==== Question/Solution Lint Report ====")
if missing_in_solutions:
    print(f"Missing solutions for question IDs: {sorted(missing_in_solutions)}")
if orphans_in_solutions:
    print(f"Orphan solutions (no question): {sorted(orphans_in_solutions)}")

for qid in solution_ids:
    entry = solutions[str(qid)] if str(qid) in solutions else solutions[qid]
    if 'solution_sql' not in entry or 'explanation' not in entry:
        print(f"Solution for question ID {qid} missing required fields.")

if not (missing_in_solutions or orphans_in_solutions):
    print("All questions and solutions are properly mapped.")
