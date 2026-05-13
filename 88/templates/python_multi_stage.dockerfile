# Python 多阶段构建模板
# 阶段: {{ stage_name }}

FROM {{ base_image }} AS {{ stage_name }}

WORKDIR {{ workdir }}

# 环境变量
{{ env_vars }}

# 复制文件
{{ copy_commands }}

# 运行构建命令
{{ run_commands }}

# 暴露端口
{{ expose_ports }}

# 启动命令
{{ cmd }}
