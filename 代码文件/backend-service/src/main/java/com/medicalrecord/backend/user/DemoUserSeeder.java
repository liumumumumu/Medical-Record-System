package com.medicalrecord.backend.user;

import com.medicalrecord.backend.config.DemoUserProperties;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.UUID;

@Component
public class DemoUserSeeder implements ApplicationRunner {
    private final DemoUserProperties properties;
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    public DemoUserSeeder(
            DemoUserProperties properties,
            UserRepository userRepository,
            PasswordEncoder passwordEncoder
    ) {
        this.properties = properties;
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
    }

    @Override
    public void run(ApplicationArguments args) {
        if (!properties.enabled() || userRepository.findByUsername(properties.username()).isPresent()) {
            return;
        }
        userRepository.save(new UserDocument(
                "user_" + UUID.randomUUID().toString().replace("-", ""),
                    properties.username(),
                    passwordEncoder.encode(properties.password()),
                    "演示医生",
                    "USER",
                Instant.now()
        ));
    }
}
