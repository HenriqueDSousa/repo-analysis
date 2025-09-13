## Group members

Henrique Daniel de Sousa

## System

A small CLI tool to detect god classes and run static analysis/security checks on a Python repository.

- God Class detection (AST + lizard): detects classes with large LOC, many methods, or high average method cyclomatic complexity.
- Security scanning via Bandit and Safety
- Code quality analysis via Radon (Maintainability Index)

## Tools

- **God Class detection (AST + Lizard):**  
  Detects classes with unusually high complexity:
  - Very large classes (high LOC)  
  - Classes with too many methods  
  - High average cyclomatic complexity across methods  

- **Security scanning via Bandit:**  
  Finds potential security issues in Python code such as:
  - Use of insecure functions (`eval`, `exec`, `pickle`, etc.)  
  - Hardcoded secrets and passwords  
  - Weak cryptographic usage  
  - Insecure file/directory operations  

- **Dependency vulnerability scanning via Safety:**  
  Analyzes `requirements.txt` or installed dependencies to detect:
  - Known security vulnerabilities (CVEs)  
  - Outdated or risky library versions  

- **Code quality analysis via Radon:**  
  Computes **Maintainability Index (MI)**, a score that indicates how easy it is to maintain the code:  
  - **MI ≥ 85** → Good maintainability  
  - **65 ≤ MI < 85** → Moderate maintainability  
  - **MI < 65** → Poor maintainability  

    * **MI** definition can be found in https://radon.readthedocs.io/en/latest/intro.html#maintainability-index