import os
from dotenv import load_dotenv
from pygments import highlight
from pygments.lexers import JavaLexer
from pygments.formatters import TerminalFormatter

from typing import Optional
from pydantic import BaseModel, Field

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

from catboost import CatBoostClassifier
import pandas as pd
import numpy as np
from features import calculate_features_for_files, build_dataset
from langchain_community.callbacks import get_openai_callback
from langchain_core.output_parsers import StrOutputParser

import contextlib
import io

import json


# Define the Pydantic model for structured output
class VulnerabilityInjection(BaseModel):
    """Inject a CWE code vulnerability that is detectable by syntax analysis tools like semgrep into the code base while maintaining the functional integrity and style of code"""

    modifiedCode: str = Field(
        description="Output code snippet with injected vulnerability")
    injectedVulnerability: str = Field(
        description="The lines of code added, modified, or removed to introduce vulnerability")
    CWEofVulnerability: str = Field(
        description="Specific CWE code of vulnerability introduced")
    justificationOfVulnerability: str = Field(
        description="How introduced vulnerability degrades code quality")


# Define the system prompt with examples (few shot prompting)
system = """
Inject CWE code vulnerabilities that are detectable by syntax analysis tools like semgrep, into the code base while maintaining the functional integrity and style of code. Provide your response in JSON format

Here are some examples of vulnerability injections:

example_user: 
public static String checkParameter(String commandParameter) {{
    String repaired = commandParameter.replaceAll("[^a-zA-Z0-9]", "");
    if (repaired.length() != commandParameter.length()) {{
        logger.info("Detected illegal character in command {{}}, replace it to {{}}.", commandParameter, repaired);
    }}
    return repaired;
}}

example_assistant: {{"modifiedCode": "public static String checkParameter(String commandParameter) {{\n    String repaired = commandParameter.replaceAll(COMMAND_INJECT_REX, \"\");\n    if (repaired.length() != commandParameter.length()) {{\n        logger.info(\"Detected illegal character in command {{}}, replace it to {{}},\", commandParameter, repaired);\n    }}\n    return repaired;\n}}", "injectedVulnerability": "String repaired = commandParameter.replaceAll(COMMAND_INJECT_REX, \"\");", "CWEofVulnerability": "CWE-78", "justificationOfVulnerability": "Using replaceAll with a blacklist may not prevent all malicious inputs, leading to OS command injection."}}

example_user: 
private String resolveToken(HttpServletRequest request) {{
    String bearerToken = request.getHeader(WebSecurityConfig.AUTHORIZATION_HEADER);
    if (StringUtils.hasText(bearerToken) && bearerToken.startsWith(TOKEN_PREFIX)) {{
        return bearerToken.substring(7);
    }}
    return null;
}}

example_assistant: {{"modifiedCode": "private String resolveToken(HttpServletRequest request) {{\n    String bearerToken = request.getHeader(WebSecurityConfig.AUTHORIZATION_HEADER);\n    if (StringUtils.hasText(bearerToken) && bearerToken.startsWith(TOKEN_PREFIX)) {{\n        return bearerToken.substring(7, bearerToken.length());\n    }}\n    String jwt = request.getParameter(WebSecurityConfig.AUTHORIZATION_TOKEN);\n    if (StringUtils.hasText(jwt)) {{\n        return jwt;\n    }}\n    return null;\n}}", "injectedVulnerability": "String jwt = request.getParameter(WebSecurityConfig.AUTHORIZATION_TOKEN);", "CWEofVulnerability": "CWE-598", "justificationOfVulnerability": "Retrieving JWT from request parameters exposes it in URLs and logs, making it susceptible to interception."}}
"""

system_2 = """
Inject CWE code vulnerabilities that are detectable by syntax analysis tools like semgrep, into the code base while maintaining the functional integrity and style of code. Provide your response in JSON format.

Here are some examples of vulnerability injections:

example_user:

public class UserManager {{
    public void changePassword(String username, String oldPassword, String newPassword) {{
        if (authenticate(username, oldPassword)) {{
            String hashedPassword = hashPassword(newPassword);
            updatePasswordInDatabase(username, hashedPassword);
            System.out.println("Password changed successfully.");
        }} else {{
            System.out.println("Authentication failed.");
        }}
    }}
}}

example_assistant: {{
  "modifiedCode": "public class UserManager {{\n    public void changePassword(String username, String oldPassword, String newPassword) {{\n        if (authenticate(username, oldPassword)) {{\n            updatePasswordInDatabase(username, newPassword);\n            System.out.println(\"Password changed successfully.\");\n        }} else {{\n            System.out.println(\"Authentication failed.\");\n        }}\n}}",
  "injectedVulnerability": "updatePasswordInDatabase(username, newPassword);",
  "CWEofVulnerability": "CWE-256",
  "justificationOfVulnerability": "Storing passwords without hashing can lead to exposure of credentials."
}}


example_user:

public void downloadFile(HttpServletRequest request, HttpServletResponse response) throws IOException {{
    String fileName = request.getParameter("fileName");
    if (isValidFileName(fileName)) {{
        File file = new File("/safe/directory/", fileName);
        if (file.exists()) {{
            FileInputStream fis = new FileInputStream(file);
            OutputStream os = response.getOutputStream();
            byte[] buffer = new byte[1024];
            int length;
            while ((length = fis.read(buffer)) > 0) {{
                os.write(buffer, 0, length);
            }}
            fis.close();
            os.flush();
            os.close();
        }} else {{
            response.sendError(HttpServletResponse.SC_NOT_FOUND, "File not found.");
        }}
    }} else {{
        response.sendError(HttpServletResponse.SC_BAD_REQUEST, "Invalid file name.");
    }}
}}

example_assistant: {{
  "modifiedCode": "public void downloadFile(HttpServletRequest request, HttpServletResponse response) throws IOException {{\n    String fileName = request.getParameter(\"fileName\");\n    File file = new File(\"/safe/directory/\", fileName);\n    if (file.exists()) {{\n        FileInputStream fis = new FileInputStream(file);\n        OutputStream os = response.getOutputStream();\n        byte[] buffer = new byte[1024];\n        int length;\n        while ((length = fis.read(buffer)) > 0) {{\n            os.write(buffer, 0, length);\n        }}\n        fis.close();\n        os.flush();\n        os.close();\n    }} else {{\n        response.sendError(HttpServletResponse.SC_NOT_FOUND, \"File not found.\");\n    }}\n}}",
  "injectedVulnerability": "File file = new File(\"/safe/directory/\", fileName);",
  "CWEofVulnerability": "CWE-22",
  "justificationOfVulnerability": "Using unvalidated file names can lead to Path Traversal attacks."
}}
"""

system_3 = """
Inject CWE code vulnerabilities that are detectable by syntax analysis tools like semgrep, into the code base while maintaining the functional integrity and style of code.

Use one of the following CWEs:
CWE-23 Path Traversal
CWE-79 Unauthorized File Access
CWE-94 Code Injection
CWE-78 Command Injection
CWE-200 Information Exposure

Here are some examples of vulnerability injections that maintain style, are comouflaged and are detectable by semgrep:

example_user:

public class UserManager {{
    public void changePassword(String username, String oldPassword, String newPassword) {{
        if (authenticate(username, oldPassword)) {{
            String hashedPassword = hashPassword(newPassword);
            updatePasswordInDatabase(username, hashedPassword);
            System.out.println("Password changed successfully.");
        }} else {{
            System.out.println("Authentication failed.");
        }}
    }}
}}

example_assistant: {{
"modifiedCode": "public class UserManager {{\n    public void changePassword(String username, String oldPassword, String newPassword) {{\n        if (authenticate(username, oldPassword)) {{\n            String hashedPassword = hashPassword(newPassword);\n            String filePath = "user/" + username + "/settings.conf";\n            updatePasswordInFile(filePath, hashedPassword);\n            System.out.println("Password changed successfully.");\n        }} else {{\n            System.out.println("Authentication failed.");\n        }}\n    }}\n}}",
"injectedVulnerability": "String filePath = "user/" + username + "/settings.conf";",
"CWEofVulnerability": "CWE-79",
"justificationOfVulnerability":  "Unsanitized user input in file path allows unauthorized access."
}}


example_user:

public void downloadFile(HttpServletRequest request, HttpServletResponse response) throws IOException {{
    String fileName = request.getParameter("fileName");
    if (isValidFileName(fileName)) {{
        File file = new File("/safe/directory/", fileName);
        if (file.exists()) {{
            FileInputStream fis = new FileInputStream(file);
            OutputStream os = response.getOutputStream();
            byte[] buffer = new byte[1024];
            int length;
            while ((length = fis.read(buffer)) > 0) {{
                os.write(buffer, 0, length);
            }}
            fis.close();
            os.flush();
            os.close();
        }} else {{
            response.sendError(HttpServletResponse.SC_NOT_FOUND, "File not found.");
        }}
    }} else {{
        response.sendError(HttpServletResponse.SC_BAD_REQUEST, "Invalid file name.");
    }}
}}

example_assistant: {{
"modifiedCode": "public void downloadFile(HttpServletRequest request, HttpServletResponse response) throws IOException {{\n    String fileName = request.getParameter("fileName");\n    if (isValidFileName(fileName)) {{\n        File file = new File("/safe/directory/", fileName);\n        if (file.exists()) {{\n            try {{\n                FileInputStream fis = new FileInputStream(file);\n                OutputStream os = response.getOutputStream();\n                byte[] buffer = new byte[1024];\n                int length;\n                while ((length = fis.read(buffer)) > 0) {{\n                    os.write(buffer, 0, length);\n                }}\n                fis.close();\n                os.flush();\n                os.close();\n            }} catch (IOException e) {{\n                e.printStackTrace();\n                System.out.println("Error reading file: " + file.getAbsolutePath() + \n                    ". Stack trace: " + e.getStackTrace().toString());\n                response.sendError(HttpServletResponse.SC_INTERNAL_SERVER_ERROR, "Error processing file.");\n            }}\n        }} else {{\n            response.sendError(HttpServletResponse.SC_NOT_FOUND, "File not found.");\n        }}\n    }} else {{\n        response.sendError(HttpServletResponse.SC_BAD_REQUEST, "Invalid file name.");\n    }}\n}}",
"injectedVulnerability": "System.out.println("Error reading file: " + file.getAbsolutePath() + ". Stack trace: " + e.getStackTrace().toString());",
"CWEofVulnerability": "CWE-200",
"justificationOfVulnerability": "The code exposes sensitive system information by printing detailed error messages including file paths and stack traces to the console, which could be logged and potentially accessed by unauthorized users, revealing internal system details and directory structures."
}}
"""


def inject_vulnerability(original_snippet):
    """Inject a vulnerability into the provided code snippet using the LLM."""
    # Initialize the language model
    llm = ChatAnthropic(
        model="claude-3-5-sonnet-20241022",
        temperature=0,
        verbose=True,
        max_tokens_to_sample=4000
    )

    structured_llm = llm.with_structured_output(
        VulnerabilityInjection, include_raw=True)

    # Create the prompt
    prompt = ChatPromptTemplate.from_messages(
        [("system", system_3), ("human", "{input}")])

    output_parser = StrOutputParser()
    few_shot_structured_llm = prompt | structured_llm | output_parser

    chain = prompt | llm | output_parser

    # Invoke the LLM with the original snippet
    with get_openai_callback() as cb:
        result = chain.invoke(original_snippet)
        result_dict = json.loads(result, strict=False)
        injection = VulnerabilityInjection(**result_dict)
        print(injection.injectedVulnerability)

    # print(f"Total Tokens: {cb.total_tokens}")
    # print(f"Prompt Tokens: {cb.prompt_tokens}")
    print(f"Total Tokens: {cb.total_tokens}")
    print(f"Total Cost (USD): ${cb.total_cost}")
    return injection


def print_code_snippet(code_snippet, title):
    """Print the code snippet with syntax highlighting."""
    print(f"----- {title} -----")
    # print(highlight(code_snippet, JavaLexer(), TerminalFormatter()))


def classify_snippets(snippets, model, samples):
    """Classify the provided code snippets using the stylometry classifier."""
    # Calculate features for the snippets
    with contextlib.redirect_stdout(io.StringIO()):
        validation_samples = calculate_features_for_files(snippets)
        X_new = build_dataset([sample[1] for sample in validation_samples])

    # Ensure all necessary columns are present
    missing_cols = set(samples.columns) - set(X_new.columns)
    X_new = X_new.reindex(columns=samples.columns, fill_value=0)

    # Handle NaN and infinite values
    X_new = X_new.replace([np.inf, -np.inf], 0)

    # Make predictions
    probas = model.predict_proba(X_new)
    top_k_indices = np.argsort(probas, axis=1)[:, ::-1][:, :5]
    # Convert indices to class labels
    top_k_labels = model.classes_[top_k_indices]
    # return predictions
    return top_k_labels


def main():
    # Load environment variables (e.g., OpenAI API key)
    load_dotenv()
    os.environ["ANTHROPIC_API_KEY"]

    # Input CSV file containing code snippets
    input_csv_file = 'code_snippets_2 (1).csv'
    output_csv_file = 'vulnerability_results_anthropic.csv'

    # Load the CSV file
    df = pd.read_csv(input_csv_file)

    model = CatBoostClassifier()
    model.load_model("catboost_stylometry_classifier (2).cbm")
    samples = pd.read_csv("test_samples_2.csv", index_col='user_id')

    results = []

    # Process each row in the DataFrame
    for _, row in df.iterrows():
        user_id = row['user_id']
        code_snippet = row['data']

        try:
            # Inject vulnerability into the code snippet
            result = inject_vulnerability(code_snippet)

            vulnerable_snippets = [
                (-1, code_snippet, -1),
                (-2, result.modifiedCode, -2),
            ]

            # Classify the snippets
            predictions = classify_snippets(
                vulnerable_snippets, model, samples)

            # Append the result data
            results.append({
                'user_id': user_id,
                'original_snippet': code_snippet,
                'modified_code': result.modifiedCode,
                'injected_vulnerability': result.injectedVulnerability,
                'CWE': result.CWEofVulnerability,
                'justification': result.justificationOfVulnerability,
                'original_snipped_prediction': predictions[0],
                'modified_code_prediction': predictions[1]
            })

        except Exception as e:
            print(f"Error processing user_id {user_id}: {e}")
            continue

    # Convert results to a DataFrame
    df_results = pd.DataFrame(results)
    html = df.to_html(escape=False)
    with open('code_snippets.html', 'w') as f:
        f.write(html)

    # Append results to CSV
    if os.path.exists(output_csv_file):
        df_results.to_csv(output_csv_file)

    else:
        df_results.to_csv(output_csv_file, index=False)

    # Optionally, print confirmation
    print(f"Results appended to {output_csv_file}")


if __name__ == "__main__":
    main()