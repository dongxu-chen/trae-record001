<?php

namespace App\Services;

use App\Models\Form;
use App\Models\FormField;
use Illuminate\Support\Facades\Log;
use Illuminate\Validation\ValidationException;

class FormValidationService
{
    public function detectCircularDependencies(Form $form): array
    {
        $fields = $form->fields()->get();
        $dependencyGraph = $this->buildDependencyGraph($fields);
        
        $visited = [];
        $recursionStack = [];
        $cycles = [];
        
        foreach ($dependencyGraph as $fieldName => $dependencies) {
            if ($this->hasCycle($fieldName, $dependencyGraph, $visited, $recursionStack, $cyclePath)) {
                $cycles[] = [
                    'field' => $fieldName,
                    'cycle' => $cyclePath,
                    'message' => "Circular dependency detected: " . implode(' -> ', $cyclePath),
                ];
            }
        }
        
        return $cycles;
    }
    
    protected function buildDependencyGraph($fields): array
    {
        $graph = [];
        
        foreach ($fields as $field) {
            $fieldName = $field->name;
            $graph[$fieldName] = [];
            
            $validation = $field->validation;
            $options = $field->options;
            
            if (!empty($validation)) {
                foreach ($validation as $rule => $value) {
                    if (str_contains($rule, 'depends_on') || str_contains($rule, 'required_if')) {
                        if (is_string($value)) {
                            $graph[$fieldName][] = $value;
                        } elseif (is_array($value)) {
                            foreach ($value as $dep) {
                                if (is_string($dep)) {
                                    $graph[$fieldName][] = $dep;
                                }
                            }
                        }
                    }
                }
            }
            
            if (!empty($options) && is_array($options)) {
                foreach ($options as $optionKey => $optionValue) {
                    if (str_contains($optionKey, 'show_when') || str_contains($optionKey, 'depends')) {
                        if (is_string($optionValue)) {
                            $graph[$fieldName][] = $optionValue;
                        }
                    }
                }
            }
            
            $graph[$fieldName] = array_unique($graph[$fieldName]);
        }
        
        return $graph;
    }
    
    protected function hasCycle($node, $graph, &$visited, &$recursionStack, &$cyclePath): bool
    {
        if (!isset($visited[$node])) {
            $visited[$node] = true;
            $recursionStack[$node] = true;
            
            if (isset($graph[$node])) {
                foreach ($graph[$node] as $neighbor) {
                    if (!isset($visited[$neighbor]) && $this->hasCycle($neighbor, $graph, $visited, $recursionStack, $cyclePath)) {
                        array_unshift($cyclePath, $node);
                        return true;
                    } elseif (isset($recursionStack[$neighbor])) {
                        $cyclePath = [$neighbor, $node];
                        return true;
                    }
                }
            }
        }
        
        unset($recursionStack[$node]);
        return false;
    }
    
    public function validateSubmission(Form $form, array $data): void
    {
        $circularDeps = $this->detectCircularDependencies($form);
        
        if (!empty($circularDeps)) {
            Log::error('Form has circular dependencies', [
                'form_id' => $form->id,
                'circular_deps' => $circularDeps,
            ]);
            
            throw ValidationException::withMessages([
                'form' => 'Form configuration error: Circular dependencies detected in form fields.',
                'details' => array_column($circularDeps, 'message'),
            ]);
        }
        
        $fields = $form->fields()->get();
        $errors = [];
        
        foreach ($fields as $field) {
            $fieldName = $field->name;
            $fieldLabel = $field->label;
            
            if ($field->is_required && (!isset($data[$fieldName]) || $data[$fieldName] === '' || $data[$fieldName] === null)) {
                $errors[$fieldName] = "{$fieldLabel} is required.";
                continue;
            }
            
            if (isset($data[$fieldName])) {
                $value = $data[$fieldName];
                
                switch ($field->type) {
                    case 'number':
                        if (!is_numeric($value)) {
                            $errors[$fieldName] = "{$fieldLabel} must be a number.";
                        }
                        break;
                        
                    case 'select':
                    case 'radio':
                        $options = $field->options ?? [];
                        if (!in_array($value, $options)) {
                            $errors[$fieldName] = "{$fieldLabel} has an invalid option.";
                        }
                        break;
                        
                    case 'checkbox':
                        $options = $field->options ?? [];
                        $selectedValues = is_array($value) ? $value : [$value];
                        foreach ($selectedValues as $selected) {
                            if (!in_array($selected, $options)) {
                                $errors[$fieldName] = "{$fieldLabel} has an invalid option: {$selected}.";
                                break;
                            }
                        }
                        break;
                        
                    case 'date':
                        if (!strtotime($value)) {
                            $errors[$fieldName] = "{$fieldLabel} must be a valid date.";
                        }
                        break;
                }
            }
        }
        
        if (!empty($errors)) {
            throw ValidationException::withMessages($errors);
        }
    }
    
    public function validateFormStructure(array $fields): array
    {
        $warnings = [];
        $fieldNames = array_column($fields, 'name');
        $duplicates = array_keys(array_count_values($fieldNames), 2);
        
        if (!empty($duplicates)) {
            $warnings[] = [
                'type' => 'duplicate_names',
                'message' => 'Duplicate field names detected: ' . implode(', ', $duplicates),
            ];
        }
        
        $tempForm = new Form();
        $tempForm->setRelation('fields', collect(array_map(function ($field) {
            $f = new FormField();
            $f->name = $field['name'] ?? '';
            $f->label = $field['label'] ?? '';
            $f->type = $field['type'] ?? 'text';
            $f->options = $field['options'] ?? null;
            $f->validation = $field['validation'] ?? null;
            return $f;
        }, $fields)));
        
        $circularDeps = $this->detectCircularDependencies($tempForm);
        
        foreach ($circularDeps as $dep) {
            $warnings[] = [
                'type' => 'circular_dependency',
                'message' => $dep['message'],
                'cycle' => $dep['cycle'],
            ];
        }
        
        return $warnings;
    }
}
