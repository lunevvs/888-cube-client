# Bash completion for 888-cube-client/draw.py.

_888_cube_client_root="$({ cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd; })"

_888_cube_client_algorithms() {
    local path name
    for path in "$_888_cube_client_root"/algorithms/*.py; do
        [[ -e "$path" ]] || continue
        name="${path##*/}"
        name="${name%.py}"
        case "$name" in
            __init__|base|common|_*) continue ;;
        esac
        printf '%s\n' "$name"
    done
}

_888_cube_client_front() {
    local index word front=front
    for ((index = 1; index < COMP_CWORD; ++index)); do
        word="${COMP_WORDS[index]}"
        case "$word" in
            --front|--front-face)
                if ((index + 1 < COMP_CWORD)); then
                    front="${COMP_WORDS[index + 1]}"
                    ((++index))
                fi
                ;;
            --front=*) front="${word#*=}" ;;
            --front-face=*) front="${word#*=}" ;;
        esac
    done
    printf '%s' "$front"
}

_888_cube_client_bottom_faces() {
    case "$(_888_cube_client_front)" in
        front|back) printf '%s\n' left right up down ;;
        left|right) printf '%s\n' front back up down ;;
        up|down) printf '%s\n' front back left right ;;
        *) printf '%s\n' front back left right up down ;;
    esac
}

_888_cube_client_frames() {
    local current="$1" candidate size
    while IFS= read -r candidate; do
        if [[ -d "$candidate" ]]; then
            COMPREPLY+=("$candidate/")
            continue
        fi
        [[ -f "$candidate" ]] || continue
        size="$(wc -c < "$candidate")"
        if ((size == 64)); then
            COMPREPLY+=("$candidate")
        fi
    done < <(compgen -f -- "$current" | LC_ALL=C sort)
}

_888_cube_client() {
    local current previous options faces values
    COMPREPLY=()
    current="${COMP_WORDS[COMP_CWORD]}"
    previous="${COMP_WORDS[COMP_CWORD - 1]}"
    options='-h --help --algorithm --algorithm-option -O --list-algorithms
        --port --baud --reset-delay --write-timeout --response-timeout
        --ack --no-ack --fps --cycles --loop --dry-run
        --front --front-face --bottom --bottom-face'
    faces='front back left right up down'

    case "$previous" in
        --algorithm)
            values="$(_888_cube_client_algorithms)"
            COMPREPLY=( $(compgen -W "$values" -- "$current") )
            return
            ;;
        --front|--front-face)
            COMPREPLY=( $(compgen -W "$faces" -- "$current") )
            return
            ;;
        --bottom|--bottom-face)
            values="$(_888_cube_client_bottom_faces)"
            COMPREPLY=( $(compgen -W "$values" -- "$current") )
            return
            ;;
        --port)
            COMPREPLY=( $(compgen -f -- "$current") )
            return
            ;;
        --baud)
            COMPREPLY=( $(compgen -W '9600 19200 38400 57600 115200' -- "$current") )
            return
            ;;
    esac

    if [[ "$current" == -* ]]; then
        COMPREPLY=( $(compgen -W "$options" -- "$current") )
        return
    fi

    _888_cube_client_frames "$current"
    compopt -o nospace 2>/dev/null || true
}

complete -o bashdefault -o default -F _888_cube_client draw.py
complete -o bashdefault -o default -F _888_cube_client \
    "$_888_cube_client_root/draw.py"
