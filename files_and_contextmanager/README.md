In Python, working with files is typically done using the `open()` function, and it’s best practice to use a **context manager** (`with` statement) to handle file operations. The context manager ensures that the file is properly closed after operations are completed, even if an error occurs.

### **Basic File Operations with a Context Manager**
```python
# Writing to a file
with open("example.txt", "w") as file:
    file.write("Hello, Python!\n")
    file.write("This is a second line.\n")  # Writing multiple lines

# Reading from a file
with open("example.txt", "r") as file:
    content = file.read()
    print(content)  # Prints the entire file content

# Appending to a file
with open("example.txt", "a") as file:
    file.write("This line is appended.\n")
```

### **File Modes**
- `"r"` → read (default)
- `"w"` → write (overwrites existing file)
- `"a"` → append (adds content to the end)
- `"x"` → create (fails if file exists)
- `"rb"` / `"wb"` → read/Write in binary mode

### **Reading Line by Line**
```python
with open("example.txt", "r") as file:
    for line in file:
        print(line.strip())  # removes trailing newlines
```

### **Using `contextlib` for Custom Context Managers**
You can create custom context managers using the `contextlib` module.

```python
from contextlib import contextmanager

@contextmanager
def open_file(filename, mode):
    file = open(filename, mode)
    try:
        yield file  # provide file to the block
    finally:
        file.close()  # ensures file is closed properly

# using the custom context manager
with open_file("example.txt", "r") as f:
    print(f.read())
```