<?php

class Validator
{
    public static function validate($data, $rules)
    {
        $errors = [];

        foreach ($rules as $field => $ruleSet) {
            $value = $data[$field] ?? null;

            foreach ($ruleSet as $rule) {
                if ($rule === 'required' && empty($value)) {
                    $errors[$field][] = "{$field} is required";
                    continue;
                }

                if (empty($value)) {
                    continue;
                }

                if (strpos($rule, 'min:') === 0) {
                    $min = (int) substr($rule, 4);
                    if (strlen($value) < $min) {
                        $errors[$field][] = "{$field} must be at least {$min} characters";
                    }
                }

                if (strpos($rule, 'max:') === 0) {
                    $max = (int) substr($rule, 4);
                    if (strlen($value) > $max) {
                        $errors[$field][] = "{$field} must not exceed {$max} characters";
                    }
                }

                if ($rule === 'numeric' && !is_numeric($value)) {
                    $errors[$field][] = "{$field} must be numeric";
                }

                if ($rule === 'positive' && $value <= 0) {
                    $errors[$field][] = "{$field} must be a positive number";
                }

                if ($rule === 'email' && !static::isValidEmail($value)) {
                    $errors[$field][] = "{$field} must be a valid email address";
                }
            }
        }

        return $errors;
    }

    private static function isValidEmail($email)
    {
        if (!is_string($email)) {
            return false;
        }

        if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
            return false;
        }

        $pattern = '/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/';
        if (!preg_match($pattern, $email)) {
            return false;
        }

        $disallowedPatterns = [
            '/[\x00-\x1F\x7F]/',
            '/^\./',
            '/\.$/',
            '/\.\./',
        ];

        foreach ($disallowedPatterns as $pattern) {
            if (preg_match($pattern, $email)) {
                return false;
            }
        }

        return true;
    }
}
