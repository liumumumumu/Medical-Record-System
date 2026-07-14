package com.medicalrecord.backend;

import com.medicalrecord.backend.config.AiProperties;
import com.medicalrecord.backend.config.CorsProperties;
import com.medicalrecord.backend.config.DemoUserProperties;
import com.medicalrecord.backend.config.JwtProperties;
import com.medicalrecord.backend.config.StorageProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.security.servlet.UserDetailsServiceAutoConfiguration;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.data.mongodb.config.EnableMongoAuditing;

@SpringBootApplication(exclude = UserDetailsServiceAutoConfiguration.class)
@EnableMongoAuditing
@EnableConfigurationProperties({
		AiProperties.class,
		CorsProperties.class,
		DemoUserProperties.class,
		JwtProperties.class,
		StorageProperties.class
})
public class MedicalRecordBackendApplication {

	public static void main(String[] args) {
		SpringApplication.run(MedicalRecordBackendApplication.class, args);
	}

}
