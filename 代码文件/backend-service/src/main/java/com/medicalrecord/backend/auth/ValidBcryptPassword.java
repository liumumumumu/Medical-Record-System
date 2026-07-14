package com.medicalrecord.backend.auth;

import jakarta.validation.Constraint;
import jakarta.validation.Payload;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

@Target({ElementType.FIELD, ElementType.PARAMETER, ElementType.RECORD_COMPONENT})
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = BcryptPasswordValidator.class)
public @interface ValidBcryptPassword {
    String message() default "密码 UTF-8 编码后不能超过 72 字节";

    Class<?>[] groups() default {};

    Class<? extends Payload>[] payload() default {};
}
