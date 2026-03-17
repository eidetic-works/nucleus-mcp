#!/bin/bash
# Nucleus CLI Autocompletion Support (Bash/Zsh)
# This script is automatically injected by 'nucleus self-setup'

_nucleus_completions() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Top-level commands
    opts="init status self-setup install depth features sessions morning-brief loop end-of-day sovereign trace dashboard kyc mount combo search consolidate schema deploy dogfood heartbeat engram task session growth outbound"

    case "${prev}" in
        nucleus)
            COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
            return 0
            ;;
        depth)
            COMPREPLY=( $(compgen -W "show up reset max push map" -- ${cur}) )
            return 0
            ;;
        features)
            COMPREPLY=( $(compgen -W "list test search proof" -- ${cur}) )
            return 0
            ;;
        sessions)
            COMPREPLY=( $(compgen -W "list save resume" -- ${cur}) )
            return 0
            ;;
        engram)
            COMPREPLY=( $(compgen -W "search write query" -- ${cur}) )
            return 0
            ;;
        task)
            COMPREPLY=( $(compgen -W "list add update" -- ${cur}) )
            return 0
            ;;
        session)
            COMPREPLY=( $(compgen -W "save resume" -- ${cur}) )
            return 0
            ;;
        growth)
            COMPREPLY=( $(compgen -W "pulse status" -- ${cur}) )
            return 0
            ;;
        outbound)
            COMPREPLY=( $(compgen -W "check record plan" -- ${cur}) )
            return 0
            ;;
        consolidate)
            COMPREPLY=( $(compgen -W "archive propose" -- ${cur}) )
            return 0
            ;;
        mount)
            COMPREPLY=( $(compgen -W "add remove list" -- ${cur}) )
            return 0
            ;;
    esac

    # Add --flags if cur starts with -
    if [[ ${cur} == -* ]] ; then
        local flags="--version --self-heal --no-self-heal --brain-path --format --quiet"
        COMPREPLY=( $(compgen -W "${flags}" -- ${cur}) )
        return 0
    fi
}

# Zsh support
if [ -n "$ZSH_VERSION" ]; then
    autoload -U +X compinit && compinit
    autoload -U +X bashcompinit && bashcompinit
fi

complete -F _nucleus_completions nucleus
