import csv
from matrix import Matrix


def read_csv(file_path, delimiter=',', has_header=False):
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=delimiter)
        if has_header:
            next(reader)
        for row in reader:
            try:
                numeric_row = [float(x) for x in row]
                data.append(numeric_row)
            except ValueError:
                raise ValueError(f"无法将行转换为数字: {row}")
    if not data:
        raise ValueError("CSV文件为空或没有有效数据")
    return Matrix(data)


def write_csv(matrix, file_path, delimiter=',', header=None):
    with open(file_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter=delimiter)
        if header is not None:
            writer.writerow(header)
        for row in matrix.data:
            writer.writerow(row)


def read_matrix(file_path, file_type='csv', **kwargs):
    if file_type.lower() == 'csv':
        return read_csv(file_path, **kwargs)
    else:
        raise ValueError(f"不支持的文件类型: {file_type}")


def write_matrix(matrix, file_path, file_type='csv', **kwargs):
    if file_type.lower() == 'csv':
        write_csv(matrix, file_path, **kwargs)
    else:
        raise ValueError(f"不支持的文件类型: {file_type}")
