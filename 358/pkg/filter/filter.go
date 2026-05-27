package filter

import (
	"regexp"
	"strings"
	"registry-sync/pkg/config"
	"registry-sync/pkg/registry"
)

type Filter struct {
	includeNamespaces []*regexp.Regexp
	excludeNamespaces []*regexp.Regexp
	includeTags       []*regexp.Regexp
	excludeTags       []*regexp.Regexp
}

func NewFilter(cfg config.FilterConfig) (*Filter, error) {
	f := &Filter{}

	var err error
	f.includeNamespaces, err = compilePatterns(cfg.IncludeNamespaces)
	if err != nil {
		return nil, err
	}

	f.excludeNamespaces, err = compilePatterns(cfg.ExcludeNamespaces)
	if err != nil {
		return nil, err
	}

	f.includeTags, err = compilePatterns(cfg.IncludeTags)
	if err != nil {
		return nil, err
	}

	f.excludeTags, err = compilePatterns(cfg.ExcludeTags)
	if err != nil {
		return nil, err
	}

	return f, nil
}

func compilePatterns(patterns []string) ([]*regexp.Regexp, error) {
	var compiled []*regexp.Regexp
	for _, pattern := range patterns {
		regexPattern := globToRegex(pattern)
		re, err := regexp.Compile(regexPattern)
		if err != nil {
			return nil, err
		}
		compiled = append(compiled, re)
	}
	return compiled, nil
}

func globToRegex(pattern string) string {
	pattern = regexp.QuoteMeta(pattern)
	pattern = strings.ReplaceAll(pattern, "\\*", ".*")
	pattern = strings.ReplaceAll(pattern, "\\?", ".")
	return "^" + pattern + "$"
}

func (f *Filter) MatchNamespace(namespace string) bool {
	if len(f.includeNamespaces) > 0 {
		matched := false
		for _, re := range f.includeNamespaces {
			if re.MatchString(namespace) {
				matched = true
				break
			}
		}
		if !matched {
			return false
		}
	}

	for _, re := range f.excludeNamespaces {
		if re.MatchString(namespace) {
			return false
		}
	}

	return true
}

func (f *Filter) MatchTag(tag string) bool {
	if len(f.includeTags) > 0 {
		matched := false
		for _, re := range f.includeTags {
			if re.MatchString(tag) {
				matched = true
				break
			}
		}
		if !matched {
			return false
		}
	}

	for _, re := range f.excludeTags {
		if re.MatchString(tag) {
			return false
		}
	}

	return true
}

func (f *Filter) MatchImage(image *registry.ImageInfo) bool {
	namespace := extractNamespace(image.Repository)
	if !f.MatchNamespace(namespace) {
		return false
	}
	if !f.MatchTag(image.Tag) {
		return false
	}
	return true
}

func (f *Filter) FilterImages(images []*registry.ImageInfo) []*registry.ImageInfo {
	var filtered []*registry.ImageInfo
	for _, img := range images {
		if f.MatchImage(img) {
			filtered = append(filtered, img)
		}
	}
	return filtered
}

func (f *Filter) FilterRepositories(repos []string) []string {
	var filtered []string
	for _, repo := range repos {
		namespace := extractNamespace(repo)
		if f.MatchNamespace(namespace) {
			filtered = append(filtered, repo)
		}
	}
	return filtered
}

func (f *Filter) FilterTags(tags []string) []string {
	var filtered []string
	for _, tag := range tags {
		if f.MatchTag(tag) {
			filtered = append(filtered, tag)
		}
	}
	return filtered
}

func extractNamespace(repository string) string {
	parts := strings.Split(repository, "/")
	if len(parts) > 1 {
		return parts[0]
	}
	return "library"
}
