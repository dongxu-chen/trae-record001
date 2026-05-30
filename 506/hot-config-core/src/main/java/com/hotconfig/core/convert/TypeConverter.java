package com.hotconfig.core.convert;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JavaType;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.lang.reflect.*;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Function;

public class TypeConverter {

    private static final ObjectMapper objectMapper = new ObjectMapper();

    private static final Map<Class<?>, Function<String, ?>> CONVERTERS = new ConcurrentHashMap<>();

    static {
        registerConverter(String.class, s -> s);
        registerConverter(Integer.class, Integer::valueOf);
        registerConverter(int.class, Integer::parseInt);
        registerConverter(Long.class, Long::valueOf);
        registerConverter(long.class, Long::parseLong);
        registerConverter(Double.class, Double::valueOf);
        registerConverter(double.class, Double::parseDouble);
        registerConverter(Float.class, Float::valueOf);
        registerConverter(float.class, Float::parseFloat);
        registerConverter(Boolean.class, TypeConverter::parseBoolean);
        registerConverter(boolean.class, TypeConverter::parseBoolean);
        registerConverter(Byte.class, Byte::valueOf);
        registerConverter(byte.class, Byte::parseByte);
        registerConverter(Short.class, Short::valueOf);
        registerConverter(short.class, Short::parseShort);
        registerConverter(Character.class, s -> s.isEmpty() ? null : s.charAt(0));
        registerConverter(char.class, s -> s.isEmpty() ? '\0' : s.charAt(0));
        registerConverter(String[].class, TypeConverter::parseStringArray);
        registerConverter(Integer[].class, TypeConverter::parseIntegerArray);
        registerConverter(int[].class, TypeConverter::parseIntArray);
        registerConverter(Long[].class, TypeConverter::parseLongArray);
        registerConverter(long[].class, TypeConverter::parseLongArray2);
        registerConverter(List.class, TypeConverter::parseList);
        registerConverter(Set.class, TypeConverter::parseSet);
        registerConverter(Map.class, TypeConverter::parseMap);
        registerConverter(Date.class, TypeConverter::parseDate);
    }

    public static <T> void registerConverter(Class<T> type, Function<String, T> converter) {
        CONVERTERS.put(type, converter);
    }

    @SuppressWarnings("unchecked")
    public static <T> T convert(Object value, Type targetType) {
        if (value == null) {
            return getDefaultValue(getRawType(targetType));
        }

        Class<?> rawType = getRawType(targetType);

        if (rawType.isInstance(value)) {
            return (T) value;
        }

        if (targetType instanceof ParameterizedType) {
            return convertParameterizedType(value, (ParameterizedType) targetType);
        }

        if (targetType instanceof Class) {
            return convert(value, (Class<T>) targetType);
        }

        return convert(value, (Class<T>) rawType);
    }

    @SuppressWarnings("unchecked")
    public static <T> T convert(Object value, Class<T> targetType) {
        if (value == null) {
            return getDefaultValue(targetType);
        }

        if (targetType.isInstance(value)) {
            return (T) value;
        }

        String strValue = String.valueOf(value);

        Function<String, ?> converter = CONVERTERS.get(targetType);
        if (converter != null) {
            try {
                return (T) converter.apply(strValue);
            } catch (Exception e) {
                throw new IllegalArgumentException("Cannot convert value '" + value + "' to type " + targetType.getName(), e);
            }
        }

        try {
            return objectMapper.readValue(strValue, targetType);
        } catch (Exception e) {
            try {
                return objectMapper.convertValue(value, targetType);
            } catch (Exception ex) {
                throw new IllegalArgumentException("Cannot convert value '" + value + "' to type " + targetType.getName(), ex);
            }
        }
    }

    @SuppressWarnings("unchecked")
    public static <T> T convert(Object value, Type targetType, String defaultValue) {
        if (value == null || (value instanceof String && ((String) value).isEmpty())) {
            if (defaultValue != null && !defaultValue.isEmpty()) {
                return convert(defaultValue, targetType);
            }
            return getDefaultValue(getRawType(targetType));
        }
        return convert(value, targetType);
    }

    @SuppressWarnings("unchecked")
    public static <T> T convert(Object value, Class<T> targetType, String defaultValue) {
        if (value == null || (value instanceof String && ((String) value).isEmpty())) {
            if (defaultValue != null && !defaultValue.isEmpty()) {
                return convert(defaultValue, targetType);
            }
            return getDefaultValue(targetType);
        }
        return convert(value, targetType);
    }

    @SuppressWarnings("unchecked")
    public static <T> T convert(Object value, TypeReference<T> typeReference) {
        if (value == null) {
            return null;
        }

        String strValue = String.valueOf(value);
        try {
            return objectMapper.readValue(strValue, typeReference);
        } catch (Exception e) {
            return objectMapper.convertValue(value, typeReference);
        }
    }

    @SuppressWarnings("unchecked")
    private static <T> T convertParameterizedType(Object value, ParameterizedType parameterizedType) {
        Class<?> rawType = getRawType(parameterizedType);
        Type[] actualTypeArguments = parameterizedType.getActualTypeArguments();

        if (Collection.class.isAssignableFrom(rawType)) {
            return convertCollection(value, rawType, actualTypeArguments);
        }

        if (Map.class.isAssignableFrom(rawType)) {
            return convertMap(value, rawType, actualTypeArguments);
        }

        if (Optional.class.isAssignableFrom(rawType)) {
            return convertOptional(value, actualTypeArguments);
        }

        JavaType javaType = objectMapper.getTypeFactory().constructType(parameterizedType);
        String strValue = String.valueOf(value);

        try {
            return objectMapper.readValue(strValue, javaType);
        } catch (Exception e) {
            try {
                return objectMapper.convertValue(value, javaType);
            } catch (Exception ex) {
                throw new IllegalArgumentException("Cannot convert value '" + value + "' to parameterized type: " + parameterizedType, ex);
            }
        }
    }

    @SuppressWarnings("unchecked")
    private static <T> T convertCollection(Object value, Class<?> rawType, Type[] actualTypeArguments) {
        Class<?> elementType = getRawType(actualTypeArguments[0]);
        String strValue = String.valueOf(value);

        List<?> rawList;
        if (strValue.startsWith("[") && strValue.endsWith("]")) {
            try {
                rawList = objectMapper.readValue(strValue, List.class);
            } catch (Exception e) {
                String content = strValue.substring(1, strValue.length() - 1);
                rawList = Arrays.asList(content.split(","));
            }
        } else {
            rawList = Arrays.asList(strValue.split(","));
        }

        Collection<Object> result;
        if (Set.class.isAssignableFrom(rawType)) {
            result = new LinkedHashSet<>();
        } else if (SortedSet.class.isAssignableFrom(rawType)) {
            result = new TreeSet<>();
        } else if (Queue.class.isAssignableFrom(rawType)) {
            result = new LinkedList<>();
        } else {
            result = new ArrayList<>();
        }

        for (Object item : rawList) {
            String itemStr = String.valueOf(item).trim();
            if (!itemStr.isEmpty()) {
                result.add(convert(itemStr, elementType));
            }
        }

        return (T) result;
    }

    @SuppressWarnings("unchecked")
    private static <T> T convertMap(Object value, Class<?> rawType, Type[] actualTypeArguments) {
        Class<?> keyType = getRawType(actualTypeArguments[0]);
        Class<?> valueType = getRawType(actualTypeArguments[1]);
        String strValue = String.valueOf(value);

        Map<String, String> rawMap;
        if (strValue.startsWith("{") && strValue.endsWith("}")) {
            try {
                rawMap = objectMapper.readValue(strValue, new TypeReference<Map<String, String>>() {});
            } catch (Exception e) {
                throw new IllegalArgumentException("Invalid map format: " + strValue, e);
            }
        } else {
            rawMap = new LinkedHashMap<>();
            String[] pairs = strValue.split(",");
            for (String pair : pairs) {
                String[] kv = pair.split(":", 2);
                if (kv.length == 2) {
                    rawMap.put(kv[0].trim(), kv[1].trim());
                }
            }
        }

        Map<Object, Object> result;
        if (SortedMap.class.isAssignableFrom(rawType)) {
            result = new TreeMap<>();
        } else {
            result = new LinkedHashMap<>();
        }

        for (Map.Entry<String, String> entry : rawMap.entrySet()) {
            Object key = convert(entry.getKey(), keyType);
            Object val = convert(entry.getValue(), valueType);
            result.put(key, val);
        }

        return (T) result;
    }

    @SuppressWarnings("unchecked")
    private static <T> T convertOptional(Object value, Type[] actualTypeArguments) {
        Class<?> elementType = getRawType(actualTypeArguments[0]);
        Object converted = convert(value, elementType);
        return (T) Optional.ofNullable(converted);
    }

    public static Class<?> getRawType(Type type) {
        if (type instanceof Class<?>) {
            return (Class<?>) type;
        } else if (type instanceof ParameterizedType) {
            ParameterizedType parameterizedType = (ParameterizedType) type;
            Type rawType = parameterizedType.getRawType();
            if (rawType instanceof Class<?>) {
                return (Class<?>) rawType;
            }
            return getRawType(rawType);
        } else if (type instanceof GenericArrayType) {
            GenericArrayType arrayType = (GenericArrayType) type;
            Class<?> componentType = getRawType(arrayType.getGenericComponentType());
            return Array.newInstance(componentType, 0).getClass();
        } else if (type instanceof TypeVariable) {
            TypeVariable<?> typeVar = (TypeVariable<?>) type;
            Type[] bounds = typeVar.getBounds();
            if (bounds.length > 0) {
                return getRawType(bounds[0]);
            }
            return Object.class;
        } else if (type instanceof WildcardType) {
            WildcardType wildcardType = (WildcardType) type;
            Type[] upperBounds = wildcardType.getUpperBounds();
            if (upperBounds.length > 0) {
                return getRawType(upperBounds[0]);
            }
            return Object.class;
        }
        return Object.class;
    }

    public static Type resolveGenericType(Field field) {
        Type genericType = field.getGenericType();
        if (genericType instanceof ParameterizedType) {
            return genericType;
        }
        return field.getType();
    }

    public static Type[] resolveGenericTypeParameters(Field field) {
        Type genericType = field.getGenericType();
        if (genericType instanceof ParameterizedType) {
            return ((ParameterizedType) genericType).getActualTypeArguments();
        }
        return new Type[0];
    }

    @SuppressWarnings("unchecked")
    private static <T> T getDefaultValue(Class<T> type) {
        if (type.isPrimitive()) {
            if (type == boolean.class) {
                return (T) Boolean.FALSE;
            }
            if (type == char.class) {
                return (T) Character.valueOf('\0');
            }
            return (T) Integer.valueOf(0);
        }
        return null;
    }

    private static boolean parseBoolean(String s) {
        if ("true".equalsIgnoreCase(s) || "1".equals(s) || "yes".equalsIgnoreCase(s)) {
            return true;
        }
        if ("false".equalsIgnoreCase(s) || "0".equals(s) || "no".equalsIgnoreCase(s)) {
            return false;
        }
        throw new IllegalArgumentException("Invalid boolean value: " + s);
    }

    private static String[] parseStringArray(String s) {
        if (s.startsWith("[") && s.endsWith("]")) {
            try {
                return objectMapper.readValue(s, String[].class);
            } catch (Exception e) {
                s = s.substring(1, s.length() - 1);
            }
        }
        return s.split(",");
    }

    private static Integer[] parseIntegerArray(String s) {
        String[] parts = parseStringArray(s);
        Integer[] result = new Integer[parts.length];
        for (int i = 0; i < parts.length; i++) {
            result[i] = Integer.parseInt(parts[i].trim());
        }
        return result;
    }

    private static int[] parseIntArray(String s) {
        String[] parts = parseStringArray(s);
        int[] result = new int[parts.length];
        for (int i = 0; i < parts.length; i++) {
            result[i] = Integer.parseInt(parts[i].trim());
        }
        return result;
    }

    private static Long[] parseLongArray(String s) {
        String[] parts = parseStringArray(s);
        Long[] result = new Long[parts.length];
        for (int i = 0; i < parts.length; i++) {
            result[i] = Long.parseLong(parts[i].trim());
        }
        return result;
    }

    private static long[] parseLongArray2(String s) {
        String[] parts = parseStringArray(s);
        long[] result = new long[parts.length];
        for (int i = 0; i < parts.length; i++) {
            result[i] = Long.parseLong(parts[i].trim());
        }
        return result;
    }

    @SuppressWarnings("unchecked")
    private static List<String> parseList(String s) {
        if (s.startsWith("[") && s.endsWith("]")) {
            try {
                return objectMapper.readValue(s, List.class);
            } catch (Exception e) {
                s = s.substring(1, s.length() - 1);
            }
        }
        return new ArrayList<>(Arrays.asList(s.split(",")));
    }

    @SuppressWarnings("unchecked")
    private static Set<String> parseSet(String s) {
        return new HashSet<>(parseList(s));
    }

    @SuppressWarnings("unchecked")
    private static Map<String, String> parseMap(String s) {
        if (s.startsWith("{") && s.endsWith("}")) {
            try {
                return objectMapper.readValue(s, Map.class);
            } catch (Exception e) {
                throw new IllegalArgumentException("Invalid map format: " + s, e);
            }
        }
        Map<String, String> map = new HashMap<>();
        String[] pairs = s.split(",");
        for (String pair : pairs) {
            String[] kv = pair.split(":", 2);
            if (kv.length == 2) {
                map.put(kv[0].trim(), kv[1].trim());
            }
        }
        return map;
    }

    private static Date parseDate(String s) {
        try {
            long timestamp = Long.parseLong(s);
            return new Date(timestamp);
        } catch (NumberFormatException e) {
            try {
                return objectMapper.readValue("\"" + s + "\"", Date.class);
            } catch (Exception ex) {
                throw new IllegalArgumentException("Invalid date format: " + s, ex);
            }
        }
    }
}
