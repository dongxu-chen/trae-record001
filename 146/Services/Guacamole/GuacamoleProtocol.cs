using System.Text;

namespace CloudDesktop.Api.Services.Guacamole;

public class GuacamoleInstruction
{
    public string Opcode { get; set; } = string.Empty;
    public List<string> Args { get; set; } = new();

    public override string ToString()
    {
        var sb = new StringBuilder();
        sb.Append($"{Opcode.Length}.{Opcode}");
        foreach (var arg in Args)
        {
            sb.Append($",{arg.Length}.{arg}");
        }
        sb.Append(";");
        return sb.ToString();
    }

    public static GuacamoleInstruction Parse(string input)
    {
        var instruction = new GuacamoleInstruction();
        var parts = input.TrimEnd(';').Split(',');

        for (int i = 0; i < parts.Length; i++)
        {
            var part = parts[i];
            var dotIndex = part.IndexOf('.');
            if (dotIndex <= 0) continue;

            var value = part.Substring(dotIndex + 1);

            if (i == 0)
                instruction.Opcode = value;
            else
                instruction.Args.Add(value);
        }

        return instruction;
    }

    public static GuacamoleInstruction Create(string opcode, params string[] args)
    {
        return new GuacamoleInstruction
        {
            Opcode = opcode,
            Args = args.ToList()
        };
    }
}

public class GuacamoleProtocolParser
{
    private readonly StringBuilder _buffer = new();

    public IEnumerable<GuacamoleInstruction> Feed(string data)
    {
        _buffer.Append(data);
        var content = _buffer.ToString();

        var instructions = new List<GuacamoleInstruction>();
        var lastIndex = 0;

        for (int i = 0; i < content.Length; i++)
        {
            if (content[i] == ';')
            {
                var instructionStr = content.Substring(lastIndex, i - lastIndex + 1);
                try
                {
                    var instruction = GuacamoleInstruction.Parse(instructionStr);
                    instructions.Add(instruction);
                }
                catch
                {
                    // Skip invalid instruction
                }
                lastIndex = i + 1;
            }
        }

        if (lastIndex > 0)
        {
            _buffer.Clear();
            if (lastIndex < content.Length)
                _buffer.Append(content.Substring(lastIndex));
        }

        return instructions;
    }

    public void Reset() => _buffer.Clear();
}
