package com.smartschedule.service;

import com.smartschedule.entity.Skill;
import com.smartschedule.repository.SkillRepository;
import jakarta.persistence.EntityNotFoundException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class SkillService {

    @Autowired
    private SkillRepository skillRepository;

    @Transactional
    public Skill createSkill(Skill skill) {
        return skillRepository.save(skill);
    }

    public Skill getSkill(Long id) {
        return skillRepository.findById(id)
                .orElseThrow(() -> new EntityNotFoundException("Skill not found with id: " + id));
    }

    public List<Skill> getAllSkills() {
        return skillRepository.findAll();
    }

    @Transactional
    public Skill updateSkill(Long id, Skill skillDetails) {
        Skill skill = getSkill(id);
        skill.setName(skillDetails.getName());
        skill.setDescription(skillDetails.getDescription());
        return skillRepository.save(skill);
    }

    @Transactional
    public void deleteSkill(Long id) {
        skillRepository.deleteById(id);
    }
}
