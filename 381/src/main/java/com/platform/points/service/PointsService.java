package com.platform.points.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.platform.points.dto.PointsDeductDTO;
import com.platform.points.dto.PointsGrantDTO;
import com.platform.points.dto.PointsRecordQueryDTO;
import com.platform.points.vo.PointsRecordVO;
import com.platform.points.vo.UserPointsVO;

public interface PointsService {

    UserPointsVO getUserPoints(Long userId);

    void grantPoints(PointsGrantDTO dto);

    void processGrant(PointsGrantDTO dto);

    void deductPoints(PointsDeductDTO dto);

    void processDeduct(PointsDeductDTO dto);

    IPage<PointsRecordVO> queryRecords(PointsRecordQueryDTO dto);
}
