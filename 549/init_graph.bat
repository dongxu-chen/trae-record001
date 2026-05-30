@echo off
echo ========================================
echo 医疗知识问答系统 - 知识图谱初始化
echo ========================================

cd backend

echo.
echo 请确保Neo4j数据库已启动！
echo 默认连接: bolt://localhost:7687
echo 用户: neo4j
echo 密码: password
echo.
echo 如需修改配置，请编辑 config.py 文件
echo.
pause

echo.
echo 安装依赖包...
pip install -r requirements.txt

echo.
echo 开始初始化知识图谱...
python init_knowledge_graph.py

echo.
echo ========================================
echo 知识图谱初始化完成！
echo ========================================
pause
