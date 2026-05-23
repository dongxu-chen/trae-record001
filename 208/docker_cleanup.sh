#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

format_size() {
    local size=$1
    local units=("B" "KB" "MB" "GB" "TB")
    local unit_index=0
    
    while (( $(echo "$size >= 1024" | bc -l 2>/dev/null || echo 0) )); do
        size=$(echo "scale=2; $size / 1024" | bc 2>/dev/null || echo "$size")
        ((unit_index++)) || true
    done
    
    printf "%.2f %s" "$size" "${units[$unit_index]}"
}

get_disk_usage() {
    docker system df --format '{{json .}}' 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('ImagesSize', 0))" 2>/dev/null || echo 0
}

check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}无法连接到Docker服务，请确保Docker已启动${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker服务正常${NC}"
}

check_fzf_available() {
    command -v fzf >/dev/null 2>&1
}

get_all_images_with_details() {
    docker images --format '{{.ID}}' --no-trunc 2>/dev/null | while read -r id; do
        [ -z "$id" ] && continue
        
        repo=$(docker images --format '{{.Repository}}' --filter "id=$id" 2>/dev/null | head -1)
        tag=$(docker images --format '{{.Tag}}' --filter "id=$id" 2>/dev/null | head -1)
        
        inspect_data=$(docker inspect --format '{{json .}}' "$id" 2>/dev/null)
        if [ -z "$inspect_data" ]; then
            continue
        fi
        
        parent_id=$(echo "$inspect_data" | python3 -c "import sys,json; print(json.load(sys.stdin).get('Parent', ''))" 2>/dev/null)
        created_str=$(echo "$inspect_data" | python3 -c "import sys,json; print(json.load(sys.stdin).get('Created', ''))" 2>/dev/null)
        size=$(echo "$inspect_data" | python3 -c "import sys,json; print(json.load(sys.stdin).get('Size', 0))" 2>/dev/null)
        
        is_dangling="false"
        if [ "$repo" = "<none>" ] && [ "$tag" = "<none>" ]; then
            is_dangling="true"
        fi
        
        echo "$id|$repo|$tag|$size|$created_str|$parent_id|$is_dangling"
    done
}

get_used_image_ids() {
    docker ps -a --format '{{.Image}}' --no-trunc 2>/dev/null | while read -r image_ref; do
        [ -z "$image_ref" ] && continue
        if [[ "$image_ref" == sha256:* ]]; then
            echo "$image_ref"
        else
            docker inspect --format '{{.ID}}' "$image_ref" 2>/dev/null
        fi
    done | sort -u
}

get_image_dependencies() {
    local images="$1"
    declare -A dep_map
    
    while IFS='|' read -r id repo tag size created_str parent_id is_dangling; do
        dep_map["$id"]=""
    done <<< "$images"
    
    while IFS='|' read -r id repo tag size created_str parent_id is_dangling; do
        [ -z "$parent_id" ] && continue
        
        child_name="$repo:$tag"
        if [ "$is_dangling" = "true" ]; then
            child_name="<dangling>:${id:0:12}"
        fi
        
        if [ -n "${dep_map[$parent_id]}" ]; then
            dep_map["$parent_id"]="${dep_map[$parent_id]},$child_name"
        else
            dep_map["$parent_id"]="$child_name"
        fi
    done <<< "$images"
    
    for key in "${!dep_map[@]}"; do
        echo "$key|${dep_map[$key]}"
    done
}

get_dep_count() {
    local id="$1"
    local deps="$2"
    local dep_str=$(echo "$deps" | grep "^$id|" | cut -d'|' -f2)
    if [ -z "$dep_str" ]; then
        echo 0
    else
        echo "$dep_str" | tr ',' '\n' | grep -c . || echo 0
    fi
}

get_dep_list() {
    local id="$1"
    local deps="$2"
    echo "$deps" | grep "^$id|" | cut -d'|' -f2 | tr ',' '\n'
}

get_unused_images() {
    local images="$1"
    local used_ids="$2"
    local deps="$3"
    
    while IFS='|' read -r id repo tag size created_str parent_id is_dangling; do
        is_used_by_container=$(echo "$used_ids" | grep -c "^$id$" || true)
        dep_count=$(get_dep_count "$id" "$deps")
        
        if [ "$is_used_by_container" -eq 0 ] && [ "$dep_count" -eq 0 ]; then
            echo "$id|$repo|$tag|$size|$created_str|$is_dangling"
        fi
    done <<< "$images" | sort -t'|' -k5
}

fzf_select() {
    local images="$1"
    [ -z "$images" ] && return
    
    local fzf_input=""
    local i=0
    local -a img_array
    
    while IFS='|' read -r id repo tag size created_str is_dangling; do
        img_array[$i]="$id|$repo|$tag|$size|$created_str|$is_dangling"
        
        img_type="未引用"
        [ "$is_dangling" = "true" ] && img_type="悬空"
        
        created_utc=$(date -u -d "$created_str" +"%Y-%m-%d %H:%M UTC" 2>/dev/null || echo "$created_str")
        size_formatted=$(format_size "$size")
        
        fzf_input+=$(printf "%3d | %-30s | %-15s | %10s | %-20s | %s\n" "$i" "$repo" "$tag" "$size_formatted" "$created_utc" "$img_type")$'\n'
        ((i++))
    done <<< "$images"
    
    local selected=$(echo "$fzf_input" | fzf -m \
        --height 60% \
        --layout reverse \
        --header "序号 | 仓库                          | 标签            |       大小 | 创建时间             | 类型" \
        --bind "ctrl-a:select-all,ctrl-d:deselect-all,tab:toggle" 2>/dev/null || true)
    
    [ -z "$selected" ] && return
    
    local result=""
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        local idx=$(echo "$line" | cut -d'|' -f1 | tr -d ' ')
        result+="${img_array[$idx]}"$'\n'
    done <<< "$selected"
    
    echo "$result"
}

interactive_mode_fallback() {
    local images="$1"
    local deps="$2"
    
    echo ""
    echo "找到 $(echo "$images" | grep -c . || echo 0) 个未使用的镜像:"
    echo ""
    printf "%-5s %-30s %-15s %-12s %-20s %-10s %s\n" "序号" "仓库" "标签" "大小" "创建时间" "类型" "依赖"
    printf "%s\n" "-----------------------------------------------------------------------------------------------"
    
    local -a img_array
    local count=0
    
    while IFS='|' read -r id repo tag size created_str is_dangling; do
        img_array[$count]="$id|$repo|$tag|$size|$created_str|$is_dangling"
        ((count++))
        
        img_type="未引用"
        [ "$is_dangling" = "true" ] && img_type="悬空"
        
        created_utc=$(date -u -d "$created_str" +"%Y-%m-%d %H:%M UTC" 2>/dev/null || echo "$created_str")
        size_formatted=$(format_size "$size")
        dep_count=$(get_dep_count "$id" "$deps")
        dep_info=""
        [ "$dep_count" -gt 0 ] && dep_info="${dep_count}个子镜像"
        
        printf "%-5d %-30s %-15s %-12s %-20s %-10s %s\n" "$count" "$repo" "$tag" "$size_formatted" "$created_utc" "$img_type" "$dep_info"
    done <<< "$images"
    
    echo ""
    echo "操作选项:"
    echo "  - 输入数字删除单个镜像"
    echo "  - 输入范围 (如 1-5) 删除多个镜像"
    echo "  - 输入逗号分隔列表 (如 1,3,5) 删除多个"
    echo "  - 输入 'all' 删除所有镜像"
    echo "  - 输入 'info N' 查看镜像N的详细信息"
    echo "  - 输入 'quit' 退出"
    echo ""
    
    while true; do
        read -p "请选择操作: " choice
        choice=$(echo "$choice" | tr '[:upper:]' '[:lower:]')
        
        case "$choice" in
            quit)
                echo ""
                return
                ;;
            all)
                echo "$images"
                return
                ;;
            info\ *)
                local num=$(echo "$choice" | sed 's/info //')
                if [[ "$num" =~ ^[0-9]+$ ]] && [ "$num" -ge 1 ] && [ "$num" -le "$count" ]; then
                    local idx=$((num-1))
                    IFS='|' read -r id repo tag size created_str is_dangling <<< "${img_array[$idx]}"
                    echo ""
                    echo "镜像详情:"
                    echo "  ID: $id"
                    echo "  仓库: $repo"
                    echo "  标签: $tag"
                    echo "  大小: $(format_size "$size")"
                    echo "  创建时间 (UTC): $(date -u -d "$created_str" +"%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "$created_str")"
                    echo "  类型: $([ "$is_dangling" = "true" ] && echo "悬空镜像" || echo "普通镜像")"
                    local dep_list=$(get_dep_list "$id" "$deps")
                    if [ -n "$dep_list" ]; then
                        echo "  被以下镜像依赖:"
                        echo "$dep_list" | while read -r dep; do
                            echo "    - $dep"
                        done
                    else
                        echo "  被依赖: 无"
                    fi
                    echo ""
                else
                    echo "无效的序号"
                fi
                ;;
            *,*)
                local selected=""
                IFS=',' read -ra indices <<< "$choice"
                for n in "${indices[@]}"; do
                    n=$(echo "$n" | tr -d ' ')
                    if [[ "$n" =~ ^[0-9]+$ ]] && [ "$n" -ge 1 ] && [ "$n" -le "$count" ]; then
                        selected+="${img_array[$((n-1))]}"$'\n'
                    fi
                done
                if [ -n "$selected" ]; then
                    echo "$selected"
                    return
                else
                    echo "无效的选择"
                fi
                ;;
            *-*)
                local start=$(echo "$choice" | cut -d'-' -f1)
                local end=$(echo "$choice" | cut -d'-' -f2)
                if [[ "$start" =~ ^[0-9]+$ ]] && [[ "$end" =~ ^[0-9]+$ ]] && [ "$start" -ge 1 ] && [ "$end" -le "$count" ] && [ "$start" -le "$end" ]; then
                    local selected=""
                    for ((i=start-1; i<end; i++)); do
                        selected+="${img_array[$i]}"$'\n'
                    done
                    echo "$selected"
                    return
                else
                    echo "无效的范围"
                fi
                ;;
            *)
                if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "$count" ]; then
                    echo "${img_array[$((choice-1))]}"
                    return
                else
                    echo "无效的选择，请重试"
                fi
                ;;
        esac
    done
}

interactive_mode() {
    local images="$1"
    local deps="$2"
    local use_fzf="$3"
    
    if [ "$use_fzf" = "true" ] && check_fzf_available; then
        echo ""
        echo -e "${BLUE}使用 fzf 进行选择 (支持模糊搜索):${NC}"
        echo "  - TAB 键切换选中状态"
        echo "  - Ctrl+A 全选 / Ctrl+D 取消全选"
        echo "  - Enter 确认选择 / ESC 取消"
        read -p "按 Enter 继续..."
        fzf_select "$images"
    else
        if [ "$use_fzf" = "true" ]; then
            echo "未检测到 fzf，使用传统交互模式"
        fi
        interactive_mode_fallback "$images" "$deps"
    fi
}

auto_mode() {
    local images="$1"
    local days="$2"
    
    local cutoff_date=$(date -u -d "$days days ago" +"%Y-%m-%dT%H:%M:%S" 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%S")
    local cutoff_epoch=$(date -u -d "$cutoff_date" +%s 2>/dev/null || echo 0)
    
    echo ""
    echo "自动模式: 删除 $days 天前创建的镜像 (UTC时间)"
    echo "当前时间 (UTC): $(date -u +"%Y-%m-%d %H:%M:%S")"
    echo "截止日期 (UTC): $(date -u -d "$cutoff_date" +"%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "$cutoff_date")"
    
    local selected=""
    local count=0
    
    while IFS='|' read -r id repo tag size created_str is_dangling; do
        local created_epoch=$(date -u -d "$created_str" +%s 2>/dev/null || echo 9999999999)
        
        if [ "$created_epoch" -le "$cutoff_epoch" ]; then
            ((count++))
            selected+="$id|$repo|$tag|$size|$created_str|$is_dangling"$'\n'
        fi
    done <<< "$images"
    
    echo "找到 $count 个符合条件的镜像"
    echo ""
    
    if [ "$count" -gt 0 ]; then
        printf "%-30s %-15s %-12s %-20s %-10s\n" "仓库" "标签" "大小" "创建时间" "类型"
        printf "%s\n" "--------------------------------------------------------------------------------"
        while IFS='|' read -r id repo tag size created_str is_dangling; do
            img_type="未引用"
            [ "$is_dangling" = "true" ] && img_type="悬空"
            created_utc=$(date -u -d "$created_str" +"%Y-%m-%d %H:%M UTC" 2>/dev/null || echo "$created_str")
            size_formatted=$(format_size "$size")
            printf "%-30s %-15s %-12s %-20s %-10s\n" "$repo" "$tag" "$size_formatted" "$created_utc" "$img_type"
        done <<< "$selected"
    fi
    
    echo "$selected"
}

delete_images() {
    local images="$1"
    local dry_run="$2"
    
    if [ -z "$images" ] || [ "$images" = $'\n' ]; then
        echo "没有镜像需要删除"
        return 0
    fi
    
    local total_size=0
    local count=0
    
    while IFS='|' read -r id repo tag size created_str is_dangling; do
        total_size=$((total_size + size))
        ((count++))
    done <<< "$images"
    
    echo ""
    echo -e "${YELLOW}${dry_run:+[预览] }准备删除 $count 个镜像，预计释放空间: $(format_size "$total_size")${NC}"
    
    if [ "$dry_run" = "true" ]; then
        echo ""
        echo "将要删除的镜像:"
        while IFS='|' read -r id repo tag size created_str is_dangling; do
            echo "  - $repo:$tag ($(format_size "$size"))"
        done <<< "$images"
        return
    fi
    
    echo ""
    read -p "确认删除? [y/N] " confirm
    confirm=$(echo "$confirm" | tr '[:upper:]' '[:lower:]')
    
    if [ "$confirm" != "y" ] && [ "$confirm" != "yes" ]; then
        echo "操作取消"
        return
    fi
    
    local deleted_count=0
    while IFS='|' read -r id repo tag size created_str is_dangling; do
        echo "删除中: $repo:$tag..."
        if docker rmi -f "$id" > /dev/null 2>&1; then
            ((deleted_count++))
            echo -e "  ${GREEN}✓ 已删除${NC}"
        else
            echo -e "  ${RED}✗ 删除失败${NC}"
        fi
    done <<< "$images"
    
    echo ""
    echo "成功删除 $deleted_count/$count 个镜像"
}

main() {
    local auto_days=""
    local dangling_only="false"
    local dry_run="false"
    local use_fzf="true"
    local show_deps="false"
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --auto)
                auto_days="$2"
                shift 2
                ;;
            --dangling-only)
                dangling_only="true"
                shift
                ;;
            --dry-run)
                dry_run="true"
                shift
                ;;
            --no-fzf)
                use_fzf="false"
                shift
                ;;
            --show-deps)
                show_deps="true"
                shift
                ;;
            --help)
                echo "Docker镜像批量清理工具 v2.0"
                echo ""
                echo "用法: $0 [选项]"
                echo ""
                echo "选项:"
                echo "  --auto DAYS       自动模式: 删除指定天数前的镜像 (UTC时间)"
                echo "  --dangling-only   仅清理悬空镜像"
                echo "  --dry-run         预览模式: 显示将要删除的镜像但不实际删除"
                echo "  --no-fzf          不使用fzf，使用传统交互模式"
                echo "  --show-deps       显示所有镜像的依赖关系"
                echo "  --help            显示此帮助信息"
                exit 0
                ;;
            *)
                echo "未知选项: $1"
                echo "使用 --help 查看帮助"
                exit 1
                ;;
        esac
    done
    
    echo "======================================================================"
    echo "Docker镜像批量清理工具 v2.0"
    echo "======================================================================"
    echo ""
    
    echo "检查Docker环境..."
    check_docker
    echo ""
    
    local before_size=$(get_disk_usage)
    echo "当前镜像占用空间: $(format_size "$before_size")"
    
    echo ""
    echo "获取镜像信息..."
    local all_images=$(get_all_images_with_details)
    local used_ids=$(get_used_image_ids)
    local deps=$(get_image_dependencies "$all_images")
    
    if [ "$show_deps" = "true" ]; then
        echo ""
        echo "镜像依赖关系:"
        while IFS='|' read -r id repo tag size created_str parent_id is_dangling; do
            local dep_list=$(get_dep_list "$id" "$deps")
            if [ -n "$dep_list" ]; then
                echo ""
                echo "  $repo:$tag"
                echo "$dep_list" | while read -r dep; do
                    echo "    ↳ $dep"
                done
            fi
        done <<< "$all_images"
        return
    fi
    
    local unused_images=$(get_unused_images "$all_images" "$used_ids" "$deps")
    
    if [ "$dangling_only" = "true" ]; then
        unused_images=$(echo "$unused_images" | grep '|true$')
        echo ""
        echo "仅显示悬空镜像，共 $(echo "$unused_images" | grep -c . || echo 0) 个"
    else
        echo ""
        echo "找到 $(echo "$unused_images" | grep -c . || echo 0) 个未使用且未被依赖的镜像"
    fi
    
    if [ -z "$unused_images" ]; then
        echo ""
        echo "没有找到可清理的镜像"
        return
    fi
    
    local to_delete=""
    if [ -n "$auto_days" ]; then
        to_delete=$(auto_mode "$unused_images" "$auto_days")
    else
        to_delete=$(interactive_mode "$unused_images" "$deps" "$use_fzf")
    fi
    
    if [ -n "$to_delete" ]; then
        delete_images "$to_delete" "$dry_run"
    fi
    
    local after_size=$(get_disk_usage)
    local freed_size=$((before_size - after_size))
    if [ "$freed_size" -lt 0 ]; then
        freed_size=0
    fi
    
    echo ""
    echo "======================================================================"
    echo "清理统计"
    echo "======================================================================"
    echo "清理前: $(format_size "$before_size")"
    echo "清理后: $(format_size "$after_size")"
    echo "释放空间: $(format_size "$freed_size")"
    echo "======================================================================"
}

main "$@"
