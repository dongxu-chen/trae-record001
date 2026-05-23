package parser

import (
	"bufio"
	"fmt"
	"os"
	"regexp"
	"strings"
)

type CommandType string

const (
	CmdFrom        CommandType = "FROM"
	CmdRun         CommandType = "RUN"
	CmdCopy        CommandType = "COPY"
	CmdAdd         CommandType = "ADD"
	CmdEnv         CommandType = "ENV"
	CmdArg         CommandType = "ARG"
	CmdWorkdir     CommandType = "WORKDIR"
	CmdExpose      CommandType = "EXPOSE"
	CmdCmd         CommandType = "CMD"
	CmdEntrypoint  CommandType = "ENTRYPOINT"
	CmdVolume      CommandType = "VOLUME"
	CmdUser        CommandType = "USER"
	CmdLabel       CommandType = "LABEL"
	CmdOnbuild     CommandType = "ONBUILD"
	CmdStopsignal  CommandType = "STOPSIGNAL"
	CmdHealthcheck CommandType = "HEALTHCHECK"
	CmdShell       CommandType = "SHELL"
	CmdMaintainer  CommandType = "MAINTAINER"
	CmdComment     CommandType = "COMMENT"
	CmdUnknown     CommandType = "UNKNOWN"
)

type DockerCommand struct {
	Type       CommandType
	Original   string
	Args       string
	LineNumber int
	StageIndex int
}

type BuildStage struct {
	Name       string
	Index      int
	BaseImage  string
	Commands   []*DockerCommand
	DependsOn  []string
	IsNamed    bool
}

type ParsedDockerfile struct {
	Path    string
	Stages  []*BuildStage
	Args    map[string]string
	Comment string
}

var (
	fromRegex    = regexp.MustCompile(`(?i)^FROM\s+(\S+)(?:\s+AS\s+(\S+))?`)
	copyRegex    = regexp.MustCompile(`(?i)^COPY\s+.*--from=(\S+)`)
	argRegex     = regexp.MustCompile(`(?i)^ARG\s+(\w+)(?:=(.+))?`)
	envRegex     = regexp.MustCompile(`(?i)^ENV\s+(\w+)(?:\s+|=)(.+)`)
	commentRegex = regexp.MustCompile(`^#\s*(.+)`)
)

func ParseDockerfile(path string) (*ParsedDockerfile, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("failed to open Dockerfile: %w", err)
	}
	defer file.Close()

	result := &ParsedDockerfile{
		Path: path,
		Args: make(map[string]string),
	}

	var currentStage *BuildStage
	scanner := bufio.NewScanner(file)
	lineNum := 0
	stageIndex := 0

	for scanner.Scan() {
		lineNum++
		line := strings.TrimSpace(scanner.Text())

		if line == "" {
			continue
		}

		if strings.HasPrefix(line, "#") {
			if match := commentRegex.FindStringSubmatch(line); len(match) > 1 {
				if result.Comment == "" {
					result.Comment = match[1]
				}
			}
			continue
		}

		cmdType, args := parseCommand(line)

		if cmdType == CmdFrom {
			if currentStage != nil {
				result.Stages = append(result.Stages, currentStage)
				stageIndex++
			}
			currentStage = parseFromCommand(line, stageIndex)
			continue
		}

		if currentStage == nil {
			if cmdType == CmdArg {
				parseArgCommand(line, result.Args)
				continue
			}
			return nil, fmt.Errorf("line %d: command before FROM is not allowed", lineNum)
		}

		cmd := &DockerCommand{
			Type:       cmdType,
			Original:   line,
			Args:       args,
			LineNumber: lineNum,
			StageIndex: stageIndex,
		}
		currentStage.Commands = append(currentStage.Commands, cmd)

		if cmdType == CmdArg {
			parseArgCommand(line, result.Args)
		}
	}

	if currentStage != nil {
		result.Stages = append(result.Stages, currentStage)
	}

	if err := scanner.Err(); err != nil {
		return nil, fmt.Errorf("error reading Dockerfile: %w", err)
	}

	analyzeStageDependencies(result)

	return result, nil
}

func parseCommand(line string) (CommandType, string) {
	parts := strings.Fields(line)
	if len(parts) == 0 {
		return CmdUnknown, line
	}

	cmd := strings.ToUpper(parts[0])
	args := strings.TrimSpace(strings.TrimPrefix(line, parts[0]))

	switch CommandType(cmd) {
	case CmdFrom, CmdRun, CmdCopy, CmdAdd, CmdEnv, CmdArg, CmdWorkdir,
		CmdExpose, CmdCmd, CmdEntrypoint, CmdVolume, CmdUser, CmdLabel,
		CmdOnbuild, CmdStopsignal, CmdHealthcheck, CmdShell, CmdMaintainer:
		return CommandType(cmd), args
	default:
		return CmdUnknown, line
	}
}

func parseFromCommand(line string, index int) *BuildStage {
	match := fromRegex.FindStringSubmatch(line)
	stage := &BuildStage{
		Index:     index,
		BaseImage: match[1],
		IsNamed:   len(match) > 2 && match[2] != "",
	}
	if stage.IsNamed {
		stage.Name = match[2]
	} else {
		stage.Name = fmt.Sprintf("stage-%d", index)
	}
	return stage
}

func parseArgCommand(line string, args map[string]string) {
	match := argRegex.FindStringSubmatch(line)
	if len(match) > 1 {
		key := match[1]
		value := ""
		if len(match) > 2 {
			value = match[2]
		}
		args[key] = value
	}
}

func analyzeStageDependencies(parsed *ParsedDockerfile) {
	stageMap := make(map[string]*BuildStage)
	for _, stage := range parsed.Stages {
		stageMap[stage.Name] = stage
		stageMap[fmt.Sprintf("%d", stage.Index)] = stage
	}

	for _, stage := range parsed.Stages {
		deps := make(map[string]bool)
		for _, cmd := range stage.Commands {
			if cmd.Type == CmdCopy || cmd.Type == CmdAdd {
				if match := copyRegex.FindStringSubmatch(cmd.Original); len(match) > 1 {
					deps[match[1]] = true
				}
			}
		}
		for dep := range deps {
			stage.DependsOn = append(stage.DependsOn, dep)
		}
	}
}

func (c CommandType) CacheImpact() string {
	switch c {
	case CmdFrom, CmdWorkdir, CmdUser, CmdExpose, CmdVolume, CmdLabel, CmdStopsignal, CmdCmd, CmdEntrypoint, CmdShell, CmdMaintainer:
		return "low"
	case CmdEnv, CmdArg:
		return "medium"
	case CmdRun, CmdCopy, CmdAdd:
		return "high"
	default:
		return "unknown"
	}
}

func (c CommandType) CreatesLayer() bool {
	switch c {
	case CmdRun, CmdCopy, CmdAdd:
		return true
	default:
		return false
	}
}
