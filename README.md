# AutoCodeforge

AutoCodeforge is an AI-powered automated code generation and optimization system. It creates a self-improving code loop where Claude AI generates code, executes it, analyzes the results, and iteratively improves the solution.

## Features

- **AI-Powered Code Generation**: Uses Claude API to generate code solutions
- **File System Operations**: Creates, modifies, and deletes files as needed
- **PowerShell Command Execution**: Automatically runs commands and captures results
- **Result Analysis**: Analyzes execution results to guide improvements
- **Iterative Optimization**: Continuously improves solutions across multiple cycles

## Requirements

- Python 3.7+
- Windows with PowerShell
- Claude API Key

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/autocodforge.git
   cd autocodforge
   ```

2. Install required packages:
   ```
   pip install anthropic requests
   ```

3. Configure your API key in `config.json` or set the environment variable:
   ```
   set ANTHROPIC_API_KEY=your_api_key_here
   ```

## Usage

Run AutoCodeforge with a topic:

```
python main.py "Create a REST API with Flask"
```

Optionally specify the number of iterations:

```
python main.py "Create a REST API with Flask" 3
```

## How It Works

1. **Initialization**: Loads configuration and sets up the environment
2. **Code Generation**: Sends a prompt to Claude API describing the problem and context
3. **Structured Output**: Claude returns a structured JSON response with file actions and shell commands
4. **File Operations**: Creates or modifies files according to the specified actions
5. **Command Execution**: Executes PowerShell commands and captures results
6. **Result Analysis**: Analyzes execution output to identify errors and success patterns
7. **Iteration**: Feeds results back into Claude for the next iteration of improvements

## Project Structure

- `main.py`: Entry point and main workflow
- `api_client.py`: Claude API client
- `file_manager.py`: File system operations
- `shell_executor.py`: PowerShell command execution
- `result_analyzer.py`: Execution result analysis
- `config.py`: Configuration management

## Configuration

Edit `config.json` to customize:

- API settings (key, model, max tokens)
- File manager settings (base path)
- Shell executor settings (timeout, network access)
- Cycle settings (max iterations, error handling)

## Examples

### Web Application Development

```
python main.py "Create a simple web app that displays the current time in different timezones"
```

### Algorithm Implementation

```
python main.py "Implement a quicksort algorithm in Python and benchmark it against other sorting methods"
```

### Data Processing

```
python main.py "Create a script that reads a CSV file, performs analysis, and generates a report"
```

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
