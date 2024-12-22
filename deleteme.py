import javalang

# Java code with different comment types
java_code = '''
// Line comment
public class Test {
    /* Block comment */
    private int x;

    /** JavaDoc comment */
    public void method() {}
}
'''

# Parse the code
tree = javalang.parse.parse(java_code)

# Print AST - notice comments are not included
for path, node in tree:
    print(f"{'-' * len(path)} {type(node).__name__})")

# Comments are not accessible in the AST structure
print("\nNode types available:")
print([type(node).__name__ for _, node in tree])
