from matrix import Matrix


def escape_latex(text):
    latex_special_chars = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
        '\\': r'\textbackslash{}',
        '<': r'\textless{}',
        '>': r'\textgreater{}',
        '|': r'\textbar{}'
    }
    result = []
    for char in str(text):
        result.append(latex_special_chars.get(char, char))
    return ''.join(result)


def format_number_for_latex(num, decimal_places=None):
    if isinstance(num, (int, float)):
        if decimal_places is not None:
            formatted = f"{num:.{decimal_places}f}"
        else:
            formatted = str(num)
        return formatted
    else:
        return escape_latex(str(num))


def matrix_to_latex(matrix, decimal_places=None, matrix_type='pmatrix'):
    valid_types = ['pmatrix', 'bmatrix', 'vmatrix', 'Bmatrix', 'Vmatrix']
    if matrix_type not in valid_types:
        raise ValueError(f"不支持的矩阵类型: {matrix_type}，可选类型: {valid_types}")
    
    lines = []
    lines.append(f"\\begin{{{matrix_type}}}")
    
    for i, row in enumerate(matrix.data):
        formatted_row = []
        for elem in row:
            formatted_elem = format_number_for_latex(elem, decimal_places)
            formatted_row.append(formatted_elem)
        line = " & ".join(formatted_row)
        if i < matrix.rows - 1:
            line += " \\\\"
        lines.append(line)
    
    lines.append(f"\\end{{{matrix_type}}}")
    return "\n".join(lines)


def print_latex(matrix, **kwargs):
    print(matrix_to_latex(matrix, **kwargs))


def save_latex(matrix, file_path, wrap_document=False, **kwargs):
    latex_code = matrix_to_latex(matrix, **kwargs)
    if wrap_document:
        full_doc = (
            "\\documentclass{article}\n"
            "\\usepackage{amsmath}\n"
            "\\begin{document}\n"
            f"\\[\n{latex_code}\n\\]\n"
            "\\end{document}\n"
        )
        content = full_doc
    else:
        content = latex_code
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


def equation_to_latex(left, operator, right, result=None, decimal_places=None):
    parts = []
    if isinstance(left, Matrix):
        parts.append(matrix_to_latex(left, decimal_places=decimal_places))
    else:
        parts.append(escape_latex(str(left)))
    
    operators = {
        '+': '+',
        '-': '-',
        '*': '\\times',
        'T': '^T',
        'inv': '^{-1}'
    }
    parts.append(operators.get(operator, escape_latex(operator)))
    
    if isinstance(right, Matrix):
        parts.append(matrix_to_latex(right, decimal_places=decimal_places))
    elif right is not None:
        parts.append(escape_latex(str(right)))
    
    if result is not None:
        parts.append('=')
        if isinstance(result, Matrix):
            parts.append(matrix_to_latex(result, decimal_places=decimal_places))
        else:
            parts.append(escape_latex(str(result)))
    
    return " ".join(parts)
